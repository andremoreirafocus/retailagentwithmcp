# Order Management MCP Server

This service is the Order Management MCP server for the Retail Support Assistant. It exposes retail order operations as MCP tools that an LLM agent can call through the backend.

## What it does

- Connects to the MySQL retail database with SQLAlchemy.
- Exposes order data and support actions through the Model Context Protocol (MCP).
- Requires an API key for every tool call.
- Returns customer-readable results for the agent to use in its response.

## Tools

| Tool | Purpose |
| --- | --- |
| `track_order` | Returns an order's status, total, tracking number, customer, dates, notes, and items. |
| `shipping_status` | Returns shipping status, tracking information, delivery address, and estimated delivery time. |
| `order_history` | Lists a customer's orders. |
| `refund_status` | Returns refund information for cancelled or returned orders. |
| `cancel_order` | Cancels an order when its status is `pending` or `processing`. |
| `return_order` | Starts a return for a delivered order and requires a reason. |

`cancel_order` and `return_order` update data in MySQL. The FastAPI agent layer is responsible for obtaining confirmation from the user before it calls them.

## Authentication

Every MCP request must include an `x-api-key` header that exactly matches `MCP_API_KEY`. The server compares keys using a constant-time comparison.

## Configuration

Create `mcp/.env` from the example file and provide the API key and MySQL connection URL:

```bash
cp mcp/.env.example mcp/.env
```

```env
MCP_API_KEY=replace-with-a-shared-secret
MYSQL_URL=mysql+pymysql://user:password@host:3306/retail_db
```

The backend must use the same `MCP_API_KEY` value. Its `ORDER_MCP_URL` should point to this service's `/mcp` endpoint.

## Run locally

From this directory, install dependencies and start the server:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The server listens on `http://localhost:8000/mcp` using the streamable HTTP transport. MySQL must be reachable before it starts.

## Docker

Docker Compose builds this directory as the `order-mcp` service and exposes port `8000`. The `backend` service connects to it at `http://order-mcp:8000/mcp` on the internal Compose network.
