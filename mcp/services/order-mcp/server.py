"""Order Management MCP Server - Customer order tools with MySQL backend."""

import os
import hmac
import logging
from mcp.server.fastmcp import FastMCP, Context
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
MYSQL_URL = os.environ.get("MYSQL_URL", "")

if not MYSQL_URL:
    raise RuntimeError("MYSQL_URL is not set. Add it to mcp/.env or the environment.")
if not MCP_API_KEY:
    raise RuntimeError("MCP_API_KEY is not set. Add it to mcp/.env or the environment.")

engine = create_engine(MYSQL_URL, pool_pre_ping=True)
mcp = FastMCP("order-management", host="0.0.0.0", port=8000)


async def get_api_key(ctx: Context) -> str:
    """Extract API key from request headers."""
    request = ctx.request_context.request
    return request.headers.get("x-api-key", "")


def verify_key(key: str) -> None:
    """Verify the API key matches using constant-time comparison."""
    if not MCP_API_KEY:
        raise ValueError("Server MCP_API_KEY not configured")
    if not key:
        raise ValueError("Missing X-API-Key header")
    if not hmac.compare_digest(key, MCP_API_KEY):
        raise ValueError("Unauthorized: invalid X-API-Key")


def _format_order_items(order_id: str) -> str:
    """Fetch and format order items for display."""
    oid = int(order_id)
    sql = text("""
        SELECT p.name, p.brand, p.sku, oi.quantity, oi.unit_price
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = :order_id
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"order_id": oid}).fetchall()

    if not rows:
        return "  No items found."

    lines = []
    for r in rows:
        line_total = r[3] * r[4]
        lines.append(f"  - {r[1]} {r[0]} (SKU: {r[2]}) x{r[3]} @ ${r[4]:.2f} = ${line_total:.2f}")
    return "\n".join(lines)


@mcp.tool()
async def track_order(order_id: str, ctx: Context) -> str:
    """Track an order by its ID. Returns order status, total, tracking number, items, and priority."""
    key = await get_api_key(ctx)
    verify_key(key)
    oid = int(order_id)
    logger.info("[TOOL] track_order(order_id=%d)", oid)

    sql = text("""
        SELECT o.id, o.status, o.total_amount, o.tracking_number,
               o.created_at, o.updated_at, o.priority, o.notes,
               c.name AS customer_name, c.email
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id = :order_id
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"order_id": oid}).fetchone()

    if not row:
        return f"Order #{oid} not found."

    items_text = _format_order_items(order_id)

    result = (
        f"Order #{row[0]}\n"
        f"Status: {row[1]}\n"
        f"Priority: {row[6]}\n"
        f"Total: ${row[2]}\n"
        f"Tracking: {row[3] or 'Not yet assigned'}\n"
        f"Customer: {row[8]} ({row[9]})\n"
        f"Created: {row[4]}\n"
        f"Last Updated: {row[5]}\n"
    )

    if row[7]:
        result += f"Notes: {row[7]}\n"

    result += f"\nOrder Items:\n{items_text}"

    return result


@mcp.tool()
async def shipping_status(order_id: str, ctx: Context) -> str:
    """Get detailed shipping status for an order."""
    key = await get_api_key(ctx)
    verify_key(key)
    oid = int(order_id)
    logger.info("[TOOL] shipping_status(order_id=%d)", oid)

    sql = text("""
        SELECT o.id, o.status, o.tracking_number, o.shipping_address,
               o.created_at, o.updated_at, c.name AS customer_name
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id = :order_id
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"order_id": oid}).fetchone()

    if not row:
        return f"Order #{oid} not found."

    status = row[1]
    tracking = row[2] or "Not yet assigned"
    address = row[3] or "No address on file"

    status_msg = {
        "pending": "Your order is pending and has not been processed yet.",
        "processing": "Your order is being prepared for shipment.",
        "shipped": f"Your order has been shipped! Tracking: {tracking}",
        "delivered": "Your order has been delivered.",
        "cancelled": "Your order has been cancelled.",
        "returned": "Your order has been returned. A refund is being processed.",
    }

    # Get delivery days from product
    sql2 = text("""
        SELECT p.delivery_days
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = :order_id LIMIT 1
    """)
    with engine.connect() as conn:
        r2 = conn.execute(sql2, {"order_id": oid}).fetchone()
    delivery_days = r2[0] if r2 else "Unknown"

    return (
        f"Order #{row[0]} Shipping Details\n"
        f"Status: {status}\n"
        f"Details: {status_msg.get(status, 'Unknown status')}\n"
        f"Tracking: {tracking}\n"
        f"Ship to: {address}\n"
        f"Customer: {row[6]}\n"
        f"Estimated delivery: {delivery_days} business days\n"
        f"Ordered: {row[4]}"
    )


@mcp.tool()
async def cancel_order(order_id: str, ctx: Context) -> str:
    """Cancel a pending or processing order. Delivered or shipped orders cannot be cancelled."""
    key = await get_api_key(ctx)
    verify_key(key)
    oid = int(order_id)
    logger.info("[TOOL] cancel_order(order_id=%d)", oid)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, status, total_amount FROM orders WHERE id = :id"),
            {"id": oid},
        ).fetchone()

        if not row:
            return f"Order #{oid} not found."

        if row[1] not in ("pending", "processing"):
            return (
                f"Order #{oid} cannot be cancelled. "
                f"Current status: {row[1]}. Only pending or processing orders can be cancelled."
            )

        conn.execute(
            text("UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE id = :id"),
            {"id": oid},
        )
        conn.commit()

    return (
        f"Order #{oid} has been successfully cancelled.\n"
        f"Refund of ${row[2]} will be processed to your original payment method within 3-5 business days."
    )


@mcp.tool()
async def return_order(order_id: str, reason: str, ctx: Context) -> str:
    """Initiate a return for a delivered order. Requires a reason for the return."""
    key = await get_api_key(ctx)
    verify_key(key)
    oid = int(order_id)
    logger.info("[TOOL] return_order(order_id=%d, reason=%s)", oid, reason)

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, status, total_amount FROM orders WHERE id = :id"),
            {"id": oid},
        ).fetchone()

        if not row:
            return f"Order #{oid} not found."

        if row[1] != "delivered":
            return (
                f"Order #{oid} cannot be returned. "
                f"Current status: {row[1]}. Only delivered orders can be returned."
            )

        conn.execute(
            text("UPDATE orders SET status = 'returned', notes = :reason, updated_at = NOW() WHERE id = :id"),
            {"id": oid, "reason": f"Return requested: {reason}"},
        )
        conn.commit()

    items_text = _format_order_items(order_id)

    return (
        f"Return initiated for Order #{oid}.\n"
        f"Reason: {reason}\n"
        f"Refund amount: ${row[2]}\n"
        f"\nOrder Items for Return:\n{items_text}\n\n"
        f"You will receive a return shipping label via email within 24 hours. "
        f"Refund will be processed within 5-7 business days after we receive the returned item."
    )


@mcp.tool()
async def refund_status(order_id: str, ctx: Context) -> str:
    """Check the refund status for a cancelled or returned order."""
    key = await get_api_key(ctx)
    verify_key(key)
    oid = int(order_id)
    logger.info("[TOOL] refund_status(order_id=%d)", oid)

    sql = text("""
        SELECT o.id, o.status, o.total_amount, o.updated_at, c.name
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.id = :id
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {"id": oid}).fetchone()

    if not row:
        return f"Order #{oid} not found."

    status = row[1]
    if status == "cancelled":
        return (
            f"Order #{row[0]} - Refund Status\n"
            f"Customer: {row[4]}\n"
            f"Amount: ${row[2]}\n"
            f"Status: Refund processed\n"
            f"Cancelled on: {row[3]}\n"
            f"Refund will appear in your account within 3-5 business days."
        )
    elif status == "returned":
        return (
            f"Order #{row[0]} - Refund Status\n"
            f"Customer: {row[4]}\n"
            f"Amount: ${row[2]}\n"
            f"Status: Awaiting return shipment\n"
            f"Returned on: {row[3]}\n"
            f"Refund will be processed after we receive the returned item."
        )
    else:
        return (
            f"Order #{row[0]} - No refund applicable.\n"
            f"Customer: {row[4]}\n"
            f"Current status: {status}. "
            f"Only cancelled or returned orders have refunds."
        )


@mcp.tool()
async def order_history(customer_id: str, ctx: Context) -> str:
    """Get all orders for a customer. Returns a summary of each order with items."""
    key = await get_api_key(ctx)
    verify_key(key)
    cid = int(customer_id)
    logger.info("[TOOL] order_history(customer_id=%d)", cid)

    sql = text("""
        SELECT o.id, o.status, o.total_amount, o.priority, o.created_at, c.name
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.customer_id = :customer_id
        ORDER BY o.created_at DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"customer_id": cid}).fetchall()

    if not rows:
        return f"No orders found for customer #{cid}."

    lines = [f"Order History for {rows[0][5]} (Customer #{cid}):", ""]
    for row in rows:
        lines.append(
            f"  Order #{row[0]} | Status: {row[1]} | "
            f"Priority: {row[3]} | Total: ${row[2]} | Date: {row[4]}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
