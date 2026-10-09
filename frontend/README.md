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

## Nginx and Docker

For production, the Dockerfile first uses Node to run `npm run build`, which creates the static files in `dist/`. A second Nginx image copies those files into its web root and serves the application on port `80`; Docker Compose maps that port to `3000` on the host.

The Nginx configuration has two important behaviors:

- It serves the compiled React files from `/usr/share/nginx/html`.
- It falls back to `index.html` for unknown paths, allowing React client-side routes to load correctly.
- It proxies requests beginning with `/api/` to `http://backend:8000` on the internal Docker Compose network.

This proxy means the browser makes requests to the same frontend origin, such as `http://localhost:3000/api/chat`, while Nginx forwards them to the FastAPI backend. The backend address is not exposed to the frontend JavaScript in the Docker deployment.
