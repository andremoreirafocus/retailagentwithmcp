"""Database operations for retail orders."""

from sqlalchemy import Engine, text


class OrderService:
    """Reads and updates orders through an injected SQLAlchemy engine."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def track_order(self, order_id: int) -> str:
        sql = text("""
            SELECT o.id, o.status, o.total_amount, o.tracking_number,
                   o.created_at, o.updated_at, o.priority, o.notes,
                   c.name AS customer_name, c.email
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.id = :order_id
        """)
        with self._engine.connect() as connection:
            row = connection.execute(sql, {"order_id": order_id}).fetchone()
        if not row:
            return f"Order #{order_id} not found."

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
        return f"{result}\nOrder Items:\n{self._format_order_items(order_id)}"

    def shipping_status(self, order_id: int) -> str:
        sql = text("""
            SELECT o.id, o.status, o.tracking_number, o.shipping_address,
                   o.created_at, o.updated_at, c.name AS customer_name
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.id = :order_id
        """)
        with self._engine.connect() as connection:
            row = connection.execute(sql, {"order_id": order_id}).fetchone()
        if not row:
            return f"Order #{order_id} not found."

        status = row[1]
        tracking = row[2] or "Not yet assigned"
        status_message = {
            "pending": "Your order is pending and has not been processed yet.",
            "processing": "Your order is being prepared for shipment.",
            "shipped": f"Your order has been shipped! Tracking: {tracking}",
            "delivered": "Your order has been delivered.",
            "cancelled": "Your order has been cancelled.",
            "returned": "Your order has been returned. A refund is being processed.",
        }

        return (
            f"Order #{row[0]} Shipping Details\n"
            f"Status: {status}\n"
            f"Details: {status_message.get(status, 'Unknown status')}\n"
            f"Tracking: {tracking}\n"
            f"Ship to: {row[3] or 'No address on file'}\n"
            f"Customer: {row[6]}\n"
            f"Estimated delivery: {self._delivery_days(order_id)} business days\n"
            f"Ordered: {row[4]}"
        )

    def cancel_order(self, order_id: int) -> str:
        with self._engine.connect() as connection:
            row = connection.execute(text("SELECT id, status, total_amount FROM orders WHERE id = :id"), {"id": order_id}).fetchone()
            if not row:
                return f"Order #{order_id} not found."
            if row[1] not in ("pending", "processing"):
                return f"Order #{order_id} cannot be cancelled. Current status: {row[1]}. Only pending or processing orders can be cancelled."
            connection.execute(text("UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE id = :id"), {"id": order_id})
            connection.commit()

        return f"Order #{order_id} has been successfully cancelled.\nRefund of ${row[2]} will be processed to your original payment method within 3-5 business days."

    def return_order(self, order_id: int, reason: str) -> str:
        with self._engine.connect() as connection:
            row = connection.execute(text("SELECT id, status, total_amount FROM orders WHERE id = :id"), {"id": order_id}).fetchone()
            if not row:
                return f"Order #{order_id} not found."
            if row[1] != "delivered":
                return f"Order #{order_id} cannot be returned. Current status: {row[1]}. Only delivered orders can be returned."
            connection.execute(
                text("UPDATE orders SET status = 'returned', notes = :reason, updated_at = NOW() WHERE id = :id"),
                {"id": order_id, "reason": f"Return requested: {reason}"},
            )
            connection.commit()

        return (
            f"Return initiated for Order #{order_id}.\nReason: {reason}\nRefund amount: ${row[2]}\n"
            f"\nOrder Items for Return:\n{self._format_order_items(order_id)}\n\n"
            "You will receive a return shipping label via email within 24 hours. "
            "Refund will be processed within 5-7 business days after we receive the returned item."
        )

    def refund_status(self, order_id: int) -> str:
        sql = text("""
            SELECT o.id, o.status, o.total_amount, o.updated_at, c.name
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.id = :id
        """)
        with self._engine.connect() as connection:
            row = connection.execute(sql, {"id": order_id}).fetchone()
        if not row:
            return f"Order #{order_id} not found."
        if row[1] == "cancelled":
            return f"Order #{row[0]} - Refund Status\nCustomer: {row[4]}\nAmount: ${row[2]}\nStatus: Refund processed\nCancelled on: {row[3]}\nRefund will appear in your account within 3-5 business days."
        if row[1] == "returned":
            return f"Order #{row[0]} - Refund Status\nCustomer: {row[4]}\nAmount: ${row[2]}\nStatus: Awaiting return shipment\nReturned on: {row[3]}\nRefund will be processed after we receive the returned item."
        return f"Order #{row[0]} - No refund applicable.\nCustomer: {row[4]}\nCurrent status: {row[1]}. Only cancelled or returned orders have refunds."

    def order_history(self, customer_id: int) -> str:
        sql = text("""
            SELECT o.id, o.status, o.total_amount, o.priority, o.created_at, c.name
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.customer_id = :customer_id
            ORDER BY o.created_at DESC
        """)
        with self._engine.connect() as connection:
            rows = connection.execute(sql, {"customer_id": customer_id}).fetchall()
        if not rows:
            return f"No orders found for customer #{customer_id}."

        lines = [f"Order History for {rows[0][5]} (Customer #{customer_id}):", ""]
        for row in rows:
            lines.append(f"  Order #{row[0]} | Status: {row[1]} | Priority: {row[3]} | Total: ${row[2]} | Date: {row[4]}")
        return "\n".join(lines)

    def _format_order_items(self, order_id: int) -> str:
        sql = text("""
            SELECT p.name, p.brand, p.sku, oi.quantity, oi.unit_price
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = :order_id
        """)
        with self._engine.connect() as connection:
            rows = connection.execute(sql, {"order_id": order_id}).fetchall()
        if not rows:
            return "  No items found."
        return "\n".join(
            f"  - {row[1]} {row[0]} (SKU: {row[2]}) x{row[3]} @ ${row[4]:.2f} = ${row[3] * row[4]:.2f}"
            for row in rows
        )

    def _delivery_days(self, order_id: int) -> int | str:
        sql = text("""
            SELECT p.delivery_days
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = :order_id LIMIT 1
        """)
        with self._engine.connect() as connection:
            row = connection.execute(sql, {"order_id": order_id}).fetchone()
        return row[0] if row else "Unknown"
