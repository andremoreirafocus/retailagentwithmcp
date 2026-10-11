# Retail Support Assistant — React + FastAPI + MCP (Day 08)

## Project intent

Retail Support Assistant is a reference application for connecting an LLM-powered support experience to retail order data. It shows how natural-language requests can be translated into bounded, explicit operations exposed through the Model Context Protocol (MCP), without giving the backend a direct database connection.

The chat interface sends questions about orders, shipping, refunds, and purchase history to an LLM agent with access to MCP tools. The tool set also includes cancellation and return operations that update an order when their status rules allow it. The agent prompt asks for confirmation before using either mutation tool, but the application does not enforce that confirmation with a workflow.

## Architecture

The runtime separates presentation, agent orchestration, domain operations, and persistence into independent components. The frontend provides the browser interface and proxies API calls to the backend. The backend accepts request-supplied conversation history, selects the LLM, and invokes MCP tools, but has no database connection. The MCP server is the only application component that performs order operations against the MySQL system of record. A one-shot database initializer waits for MySQL health, then creates the schema and imports the baseline data; the other application services are not gated on its completion.

| # | Component | Tech | Port | Directory |
|---|-----------|------|------|-----------|
| 1 | MCP server | FastMCP + SQLAlchemy | `8000` | `mcp/services/order-mcp/` |
| 2 | Backend API | FastAPI + LangChain agent | `8001` | `backend/` |
| 3 | Frontend | React (Vite) + Nginx | `5173` (dev) / `3000` (Docker) | `frontend/` |
| 4 | MySQL | MySQL 8.4 | `3306` | Docker volume `mysql_data` |
| 5 | Database initializer | Python + SQLAlchemy | — | `db-init/` |

```
Browser ──> React (:5173) ──/api──> FastAPI (:8001) ──streamable HTTP──> MCP (:8000) ──> MySQL
                                     (Groq LLM + tools)
```

1. **React frontend** presents the chat interface, sends messages to the backend, and displays the assistant's reply and MCP health status. See the [frontend README](frontend/README.md).
2. **FastAPI backend** receives chat requests, supplies conversation history to a LangChain agent, and connects that agent to the MCP tools. It can use Groq or a local/remote Ollama model. See the [backend README](backend/README.md).
3. **Order Management MCP server** exposes authenticated order tools, such as order tracking, shipping status, refunds, cancellations, and returns. It queries and updates the MySQL retail database. See the [MCP server README](mcp/services/order-mcp/README.md).
4. **MySQL** stores customers, orders, order items, and products. Docker Compose reads its configuration and the shared MCP API key from the root `.env` file.
5. **Database initializer** creates the schema and imports the CSV data only when the database is empty. See the [database initializer README](db-init/README.md).

For a typical request, the browser sends a question to `POST /api/chat`; the backend's agent decides whether it needs an order tool; the MCP server executes the database operation; and the agent returns a customer-friendly answer to the browser.



## Run with Docker

Copy the Compose environment template, then set the MySQL, MCP, and selected LLM provider values:

```powershell
Copy-Item .env.example .env
```

```powershell
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend (nginx) | http://localhost:3000 |
| Backend API docs | http://localhost:8001/docs |
| MCP server | http://localhost:8000/mcp |


```powershell
docker compose ps        # frontend, backend, order-mcp, and mysql should be running; db-init exits after success
docker compose logs -f backend
docker compose down
```

## Choose LLM provider (Groq or Ollama)

One switch in the root `.env`:

```env
LLM_PROVIDER=groq      # or: ollama
```

| Provider | Settings in the root `.env` |
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

1. Open http://localhost:3000 — header shows **MCP connected · 6 tools** (green dot).
2. Click a suggestion or type a question, press Enter.

| Question | Expected behaviour |
|---|---|
| `Where is order 100004 and what is its delivery status?` | `shipping_status` → delivered, tracking, ship-to address |
| `Show me the full details and items for order 100001` | `track_order` → pending order, total, line items |
| `What orders does customer 50001 have?` | `order_history` → list with status/total/date |
| `Cancel order 100008` | The agent is prompted to ask for confirmation; `cancel_order` can update pending or processing orders when invoked. |
| `What is the refund status of order 100002?` | `refund_status` → refund details for the returned order |
| `Where is order 999999?` | "not found" reported, nothing invented |

Red status dot = backend or MCP unreachable — check the Compose logs.
