# Retail Support Assistant — React + FastAPI + MCP (Day 08)

## Project intent

This project demonstrates a retail customer-support assistant built around an LLM agent and the Model Context Protocol (MCP). Customers can ask natural language questions about orders, shipping, refunds, and purchase history. The assistant chooses the appropriate MCP tool to retrieve live order information and can initiate eligible cancellations or returns after confirmation.

The application keeps responsibilities separate: the user interface handles the conversation, the backend orchestrates the LLM agent, and the MCP service owns access to order data in MySQL.

## Architecture

Three separate applications that talk to each other:

| # | App | Tech | Port | Directory |
|---|-----|------|------|-----------|
| 1 | MCP server | FastMCP + MySQL | `8000` | `mcp/services/order-mcp/` |
| 2 | Backend API | FastAPI + LangChain agent | `8001` | `backend/` |
| 3 | Frontend | React (Vite) | `5173` (dev) / `3000` (docker) | `frontend/` |

```
Browser ──> React (:5173) ──/api──> FastAPI (:8001) ──streamable HTTP──> MCP (:8000) ──> MySQL
                                     (Groq LLM + tools)
```

1. **React frontend** presents the chat interface, sends messages to the backend, and displays the assistant's reply and MCP health status.
2. **FastAPI backend** receives chat requests, supplies conversation history to a LangChain agent, and connects that agent to the MCP tools. It can use Groq or a local/remote Ollama model.
3. **Order Management MCP server** exposes authenticated order tools, such as order tracking, shipping status, refunds, cancellations, and returns. It queries and updates the MySQL retail database.
4. **MySQL** stores customers, orders, order items, and products. It is an external dependency configured through `mcp/.env`.

For a typical request, the browser sends a question to `POST /api/chat`; the backend's agent decides whether it needs an order tool; the MCP server executes the database operation; and the agent returns a customer-friendly answer to the browser.



## Run with Docker

```powershell
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend (nginx) | http://localhost:3000 |
| Backend API docs | http://localhost:8001/docs |
| MCP server | http://localhost:8000/mcp |


```powershell
docker compose ps        # all three should be running
docker compose logs -f backend
docker compose down
```

## Choose LLM provider (Groq or Ollama)

One switch in `backend/.env`:

```env
LLM_PROVIDER=groq      # or: ollama
```

| Provider | Settings in `backend/.env` |
|---|---|
| `groq` | `GROQ_API_KEY`, `GROQ_MODEL` (e.g. `openai/gpt-oss-120b`) |
| `ollama` | `OLLAMA_BASE_URL` (`http://localhost:11434`), `OLLAMA_MODEL` (must be pulled, e.g. `ollama pull qwen2.5:3b`) |

Restart the backend after switching. The active provider shows in the UI header
(`MCP connected · 6 tools · ollama: qwen2.5:3b`) and in `GET /api/health`.

```powershell
Invoke-RestMethod http://localhost:8001/api/health   # -> provider / model
```

Docker: compose sets `OLLAMA_BASE_URL=http://host.docker.internal:11434` so the
backend container reaches Ollama running on your machine. For a remote Ollama:

```powershell
$env:OLLAMA_BASE_URL = "http://192.168.1.5:11434"
docker compose up -d backend --force-recreate
```

## Sample data

| Entity | IDs |
|---|---|
| Orders | `100001` pending, `100002` returned, `100003` shipped, `100004` delivered, `100007` processing, `100008` pending |
| Customers | `50001` Sarah Johnson, `50002` Mike Chen, `50003` James Wilson |

Note: `cancel_order` / `return_order` change database state — use disposable test orders.



### Frontend

1. Open http://localhost:5173 — header shows **MCP connected · 6 tools** (green dot).
2. Click a suggestion or type a question, press Enter.

| Question | Expected behaviour |
|---|---|
| `Where is order 100004 and what is its delivery status?` | `shipping_status` → delivered, tracking, ship-to address |
| `Show me the full details and items for order 100001` | `track_order` → pending order, total, line items |
| `What orders does customer 50001 have?` | `order_history` → list with status/total/date |
| `Cancel order 100008` | Agent asks for confirmation first, then `cancel_order` (pending/processing only) |
| `What is the refund status of order 100002?` | `refund_status` → refund details for the returned order |
| `Where is order 999999?` | "not found" reported, nothing invented |

Red status dot = backend or MCP unreachable — check the three terminals.
