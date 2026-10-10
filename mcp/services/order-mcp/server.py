"""FastMCP server construction, tool registration, and entrypoint."""

import hmac
import logging

from mcp.server.fastmcp import Context, FastMCP
from sqlalchemy import create_engine

from order_service import OrderService
from settings import Settings

logger = logging.getLogger(__name__)


def create_mcp_server(settings: Settings) -> FastMCP:
    """Build an MCP server with explicitly supplied configuration and dependencies."""

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    service = OrderService(engine)
    mcp = FastMCP("order-management", host="0.0.0.0", port=8000)

    @mcp.tool()
    async def track_order(order_id: str, ctx: Context) -> str:
        """Track an order by its ID. Returns order status, total, tracking number, items, and priority."""
        order_id_value = _authorize_and_parse_id(order_id, ctx, settings.mcp_api_key, "Order ID")
        logger.info("[TOOL] track_order(order_id=%d)", order_id_value)
        return service.track_order(order_id_value)

    @mcp.tool()
    async def shipping_status(order_id: str, ctx: Context) -> str:
        """Get detailed shipping status for an order."""
        order_id_value = _authorize_and_parse_id(order_id, ctx, settings.mcp_api_key, "Order ID")
        logger.info("[TOOL] shipping_status(order_id=%d)", order_id_value)
        return service.shipping_status(order_id_value)

    @mcp.tool()
    async def cancel_order(order_id: str, ctx: Context) -> str:
        """Cancel a pending or processing order. Delivered or shipped orders cannot be cancelled."""
        order_id_value = _authorize_and_parse_id(order_id, ctx, settings.mcp_api_key, "Order ID")
        logger.info("[TOOL] cancel_order(order_id=%d)", order_id_value)
        return service.cancel_order(order_id_value)

    @mcp.tool()
    async def return_order(order_id: str, reason: str, ctx: Context) -> str:
        """Initiate a return for a delivered order. Requires a reason for the return."""
        order_id_value = _authorize_and_parse_id(order_id, ctx, settings.mcp_api_key, "Order ID")
        return_reason = _parse_reason(reason)
        logger.info("[TOOL] return_order(order_id=%d)", order_id_value)
        return service.return_order(order_id_value, return_reason)

    @mcp.tool()
    async def refund_status(order_id: str, ctx: Context) -> str:
        """Check the refund status for a cancelled or returned order."""
        order_id_value = _authorize_and_parse_id(order_id, ctx, settings.mcp_api_key, "Order ID")
        logger.info("[TOOL] refund_status(order_id=%d)", order_id_value)
        return service.refund_status(order_id_value)

    @mcp.tool()
    async def order_history(customer_id: str, ctx: Context) -> str:
        """Get all orders for a customer. Returns a summary of each order with items."""
        customer_id_value = _authorize_and_parse_id(customer_id, ctx, settings.mcp_api_key, "Customer ID")
        logger.info("[TOOL] order_history(customer_id=%d)", customer_id_value)
        return service.order_history(customer_id_value)

    return mcp


def _authorize_and_parse_id(raw_id: str, ctx: Context, api_key: str, label: str) -> int:
    provided_key = ctx.request_context.request.headers.get("x-api-key", "")
    if not provided_key:
        raise ValueError("Missing X-API-Key header")
    if not hmac.compare_digest(provided_key, api_key):
        raise ValueError("Unauthorized: invalid X-API-Key")
    return _parse_positive_id(raw_id, label)


def _parse_positive_id(raw_id: str, label: str) -> int:
    try:
        value = int(raw_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a positive whole number.") from exc
    if value <= 0:
        raise ValueError(f"{label} must be a positive whole number.")
    return value


def _parse_reason(reason: str) -> str:
    value = reason.strip()
    if not value:
        raise ValueError("A reason is required to start a return.")
    return value


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    mcp = create_mcp_server(Settings())
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
