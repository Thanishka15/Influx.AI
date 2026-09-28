"""FastAPI facade for an OpenClaw Social Media Agent with official Hindsight memory."""
import os
from typing import Any
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

GATEWAY = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789").rstrip("/")
GATEWAY_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN")
AGENT = os.getenv("OPENCLAW_AGENT_ID", "social-media-agent")
HINDSIGHT = os.getenv("HINDSIGHT_API_URL", "http://127.0.0.1:9077").rstrip("/")
HINDSIGHT_TOKEN = os.getenv("HINDSIGHT_API_TOKEN")
BANK = os.getenv("HINDSIGHT_BANK_ID", "social-media-agent")

SYSTEM_PROMPT = """
You are Memento, an AI Social Media Engagement Agent.

Your purpose is to help creators grow by learning from previous conversations and audience behavior stored in Hindsight memory.

Always:
- Give specific, actionable advice.
- Never give generic motivational responses.
- When suggesting content, provide:
  1. One best content idea.
  2. A 10–20 second script.
  3. Hook.
  4. Caption.
  5. Hashtags.
  6. Best posting time.
  7. Explain how it matches remembered audience patterns.
"""

app = FastAPI(title="Social Memory Agent API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str = Field(default="social-memory-ui", min_length=1, max_length=120)

class ChatResponse(BaseModel):
    reply: str

class AnalyticsRequest(BaseModel):
    post_type: str = Field(min_length=1, max_length=50)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    shares: int = Field(ge=0)

def headers(token: str | None) -> dict[str, str]:
    result = {"Content-Type": "application/json"}
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result

def unavailable(name: str, guidance: str, exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"{name} is unavailable. Complete the OpenClaw + Hindsight CLI setup and start the gateway. {guidance}")

async def hindsight_list(limit: int = 50) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{HINDSIGHT}/v1/default/banks/{BANK}/memories/list", headers=headers(HINDSIGHT_TOKEN), params={"limit": min(max(limit, 1), 100)})
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise unavailable("Hindsight", "Verify its endpoint, bank ID, and token.", exc) from exc

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "memory_provider": "openclaw-hindsight"}

@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Hindsight auto-recalls before and auto-retains after this OpenClaw turn."""
    body = {"model": f"openclaw/{AGENT}", "user": f"conv:{payload.conversation_id}", "stream": False, "messages": [{"role": "system", "content": SYSTEM_PROMPT},{"role": "user", "content": payload.message}]}
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{GATEWAY}/v1/chat/completions", headers=headers(GATEWAY_TOKEN), json=body)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        raise unavailable("OpenClaw Gateway", "Enable gateway.http.endpoints.chatCompletions.", exc) from exc
    try:
        return ChatResponse(reply=data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="OpenClaw returned an unexpected chat response.") from exc

@app.get("/memory")
async def memory(limit: int = 50) -> dict[str, Any]:
    """Read the Hindsight bank, the only source of memory."""
    return await hindsight_list(limit)

@app.get("/analytics")
async def analytics(limit: int = 50) -> dict[str, Any]:
    """Return Hindsight entries created through the analytics endpoint."""
    records = await hindsight_list(100)
    items = [item for item in records.get("items", []) if item.get("metadata", {}).get("source") == "social-analytics"]
    return {"items": items[:min(max(limit, 1), 100)], "total": len(items)}

@app.post("/analytics", status_code=status.HTTP_202_ACCEPTED)
async def add_analytics(payload: AnalyticsRequest) -> dict[str, str]:
    """Retain manual performance data directly into the configured Hindsight bank."""
    content = f"Social analytics entry: {payload.post_type} received {payload.likes} likes, {payload.comments} comments, and {payload.shares} shares."
    body = {"items": [{"content": content, "metadata": {"source": "social-analytics", "post_type": payload.post_type, "likes": str(payload.likes), "comments": str(payload.comments), "shares": str(payload.shares)}}]}
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{HINDSIGHT}/v1/default/banks/{BANK}/memories", headers=headers(HINDSIGHT_TOKEN), json=body)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise unavailable("Hindsight", "Verify its endpoint, bank ID, and token.", exc) from exc
    return {"status": "accepted", "message": "Analytics retained in Hindsight."}

