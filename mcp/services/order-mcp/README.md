# Order Management MCP Server

This service is the Order Management MCP server for the Retail Support Assistant. It exposes retail order operations as MCP tools that an LLM agent can call through the backend.

## Architecture

- `server.py` creates and starts the FastMCP server, registers MCP tool functions, and validates MCP requests.
- `settings.py` loads and validates the MCP API key and database URL with Pydantic Settings.
- `order_service.py` contains the `OrderService` class, which performs the MySQL queries and updates through its injected SQLAlchemy engine.

This keeps configuration, MCP transport concerns, and database operations separate. The server has no module-level configuration, database engine, or tool dependencies.

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

`cancel_order` and `return_order` update data in MySQL. The backend's system prompt tells the agent to ask for confirmation before it calls them, but the MCP server does not enforce a confirmation workflow.

## Authentication

Every MCP request must include an `x-api-key` header that exactly matches `MCP_API_KEY`. The server compares keys using a constant-time comparison.

## Configuration

The service environment contract is documented in `mcp/.env.example`. With Docker Compose, set `MCP_API_KEY` in the root `.env` file. Docker Compose supplies the server's `DATABASE_URL` from the same file's MySQL configuration and injects the API key into both the MCP server and backend.

For a standalone run, copy `mcp/.env.example` to `mcp/.env` and set its values for the target database.

The backend's `ORDER_MCP_URL` should point to this service's `/mcp` endpoint.

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

Docker Compose builds this directory as the `order-mcp` service and exposes port `8000`. The `backend` service connects to it at `http://order-mcp:8000/mcp` on the internal Compose network. Run the full Compose stack so MySQL and `db-init` are also started.
