# Retail Support Frontend

This is the web user interface for the Retail Support Assistant. It is a React single-page application built with Vite.

## What it does

- Displays a chat interface for customer-support questions.
- Shows suggested questions for order tracking, order details, purchase history, and refunds.
- Sends messages and recent chat history to the backend agent.
- Renders the assistant's replies, loading state, and request errors.
- Checks the backend health endpoint and shows whether the MCP service is available, along with the active LLM provider, model, and tool count.

## How it works

When the application starts, it requests `GET /api/health` to determine whether the backend and MCP service are reachable. The response drives the status label in the header.

When a user sends a message, the application adds it to the chat, then sends a `POST /api/chat` request with the message and prior chat messages:

```json
{
  "message": "Where is order 100004?",
  "history": [
    {"role": "user", "content": "Show my recent order"},
    {"role": "assistant", "content": "Which order ID should I check?"}
  ]
}
```

The FastAPI backend runs the LLM agent, which can call order tools through the MCP service. The frontend displays the returned `reply` field as the next assistant message.

## Run locally

Install dependencies and start the Vite development server:

```bash
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Vite proxies requests starting with `/api` to `http://localhost:8001`, so the backend must be running on that port.

## Docker

The Docker build creates static production files and serves them with Nginx on port `3000` through Docker Compose. Nginx proxies `/api` requests to the `backend` Compose service.
