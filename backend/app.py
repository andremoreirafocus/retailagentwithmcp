"""Retail support backend: FastAPI + LangChain agent over the order MCP service."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field

import httpx

ORDER_MCP_URL = os.environ.get("ORDER_MCP_URL", "http://localhost:8000/mcp")
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "groq").lower()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

if LLM_PROVIDER not in ("groq", "ollama"):
    raise RuntimeError("LLM_PROVIDER must be 'groq' or 'ollama' (backend/.env).")

if LLM_PROVIDER == "groq" and not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY is not set. Add it to backend/.env or the environment.")

if not MCP_API_KEY:
    raise RuntimeError("MCP_API_KEY is not set. Add it to backend/.env or the environment.")


def build_model():
    """Chat model selected by LLM_PROVIDER (groq | ollama)."""
    if LLM_PROVIDER == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            num_ctx=int(os.environ.get("OLLAMA_NUM_CTX", "8192")),
            num_predict=int(os.environ.get("OLLAMA_NUM_PREDICT", "1024")),
        )
    return ChatGroq(model=GROQ_MODEL, temperature=0)


def active_model_name() -> str:
    return OLLAMA_MODEL if LLM_PROVIDER == "ollama" else GROQ_MODEL

SYSTEM_PROMPT = """You are a retail customer support agent with access to an order MCP service.

Tools:
- track_order: full order details (status, total, tracking, items)
- shipping_status: shipping/delivery details for an order
- order_history: all orders for a customer
- refund_status: refund state for a cancelled or returned order
- cancel_order: cancel an order (pending/processing only)
- return_order: start a return for a delivered order (needs a reason)

Rules:
- Explain things clearly, helpfully and concisely
- Use order tools for order/shipping/refund questions
- Do not invent customer or order information
- Before calling cancel_order or return_order, confirm the order ID and intent with the user
- If a tool returns an error or 'not found', tell the user instead of guessing
"""

@asynccontextmanager
async def lifespan(_: FastAPI):
    print(f"[startup] LLM: {LLM_PROVIDER} | model: {active_model_name()}", flush=True)

    if LLM_PROVIDER == "ollama":
        try:
            httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5).raise_for_status()
            print(f"[startup] LLM: OK - Ollama reachable at {OLLAMA_BASE_URL}", flush=True)
        except Exception as exc:
            print(f"[startup] LLM: FAILED - Ollama not reachable at {OLLAMA_BASE_URL} ({exc})", flush=True)
    else:
        print("[startup] LLM: OK - Groq API key configured", flush=True)

    try:
        tools = await get_tools()
        names = ", ".join(t.name for t in tools)
        print(f"[startup] MCP: OK - connected to {ORDER_MCP_URL} ({len(tools)} tools: {names})", flush=True)
    except Exception as exc:
        print(f"[startup] MCP: FAILED - could not connect to {ORDER_MCP_URL} ({exc})", flush=True)

    yield


app = FastAPI(title="Retail Support API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

class ChatResponse(BaseModel):
    reply: str
    model: str

class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
    mcp_url: str
    tools: list[str]

async def get_tools():
    client = MultiServerMCPClient(
        {
            "order": {
                "transport": "streamable_http",
                "url": ORDER_MCP_URL,
                "headers": {"x-api-key": MCP_API_KEY} if MCP_API_KEY else {},
            }
        }
    )
    return await client.get_tools()


def build_messages(req: ChatRequest) -> list:
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for item in req.history[-10:]:
        if item.role == "user":
            messages.append(HumanMessage(content=item.content))
        else:
            messages.append(AIMessage(content=item.content))
    messages.append(HumanMessage(content=req.message))
    return messages


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        tools = await get_tools()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MCP unreachable: {exc}") from exc
    return HealthResponse(
        status="ok",
        provider=LLM_PROVIDER,
        model=active_model_name(),
        mcp_url=ORDER_MCP_URL,
        tools=[t.name for t in tools],
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    try:
        tools = await get_tools()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"MCP unreachable: {exc}") from exc

    agent = create_agent(model=build_model(), tools=tools, system_prompt=SYSTEM_PROMPT)

    try:
        response = await agent.ainvoke({"messages": build_messages(req)})
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent error: {exc}") from exc

    return ChatResponse(reply=response["messages"][-1].content, model=active_model_name())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000)
