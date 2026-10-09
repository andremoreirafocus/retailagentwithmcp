# Retail Support Backend

This service is the API and agent layer for the Retail Support Assistant. It
accepts chat messages from the frontend, uses an LLM to decide which order
tool is relevant, and calls the Order Management MCP service to retrieve or
change order data.

The MCP service exposes the order tools the agent can use, including access to a orders database 

## What it does

- Provides a FastAPI API for the chat frontend.
- Connects to the Order Management MCP server over streamable HTTP.
- Builds a LangChain agent for each chat request.
- Supports Groq and Ollama as the LLM provider.
- Supplies the agent with recent conversation history and retail-support
  instructions.
- Reports the active model and available MCP tools through a health endpoint.

The agent can use these MCP tools:

- `track_order` for full order details and line items.
- `shipping_status` for delivery and tracking details.
- `order_history` for a customer's orders.
- `refund_status` for cancelled or returned orders.
- `cancel_order` to cancel pending or processing orders.
- `return_order` to begin a return for a delivered order.

Cancellation and return operations change order state. The agent is instructed
to ask for confirmation before it calls either tool.

## API

### `GET /api/health`

Checks that the backend can reach the MCP service and returns the configured
LLM provider, model, MCP URL, and discovered tool names.

Example response:

```json
{
  "status": "ok",
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "mcp_url": "http://localhost:8000/mcp",
  "tools": ["track_order", "shipping_status"]
}
```

### `POST /api/chat`

Accepts a user message and optional recent chat history, then returns the
agent's reply and the active model.

```json
{
  "message": "Where is order 100004?",
  "history": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "How can I help?"}
  ]
}
```

```json
{
  "reply": "Order 100004 has been delivered.",
  "model": "qwen2.5:3b"
}
```

## Configuration

Copy the example file and set the required values:

```bash
cp .env.example .env
```

`MCP_API_KEY` must match the key configured for the MCP service. Choose one
LLM provider with `LLM_PROVIDER`:

| Provider | Required settings |
| --- | --- |
| Groq | `GROQ_API_KEY`, optionally `GROQ_MODEL` |
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_MODEL` |

Set `ORDER_MCP_URL` to the MCP endpoint. For local development, its usual
value is `http://localhost:8000/mcp`. Docker Compose overrides it with the
internal service address.

## Run locally

Install the dependencies and start the API:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8001
```

The MCP service must already be running and reachable. OpenAPI documentation
is available at [http://localhost:8001/docs](http://localhost:8001/docs).

## Run with Docker Compose

From the repository root:

```bash
docker compose up --build backend
```

The API is exposed on port `8001`. Compose configures the backend to call the
`order-mcp` container at `http://order-mcp:8000/mcp`.

## Errors

- `400`: the chat message is empty.
- `503`: the MCP service cannot be reached.
- `502`: the agent or configured LLM provider returned an error.
