"""Influx.AI API: FastAPI facade over OpenClaw Gateway and Hindsight Cloud."""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

GATEWAY_URL = os.getenv("OPENCLAW_GATEWAY_URL", "http://127.0.0.1:18789").rstrip("/")
GATEWAY_TOKEN = os.getenv("OPENCLAW_GATEWAY_TOKEN")
GATEWAY_MODEL = os.getenv("OPENCLAW_MODEL", "openclaw/main").strip()
HINDSIGHT_URL = os.getenv("HINDSIGHT_API_URL", "https://api.hindsight.vectorize.io").rstrip("/")
HINDSIGHT_TOKEN = os.getenv("HINDSIGHT_API_TOKEN")
HINDSIGHT_BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "influx-ai-creator")
PROFILE_DB_PATH = Path(os.getenv("INFLUX_PROFILE_DB", str(Path(__file__).parent / "data" / "influx-ai.db")))
CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
ANALYTICS_SOURCES = {"influx-ai-analytics", "memento-analytics"}
logger = logging.getLogger("influx_ai.gateway")

app = FastAPI(title="Influx.AI API", version="1.1.0")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    conversation_id: str = Field(min_length=1, max_length=160)
    user_id: str = Field(min_length=1, max_length=160)


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


class ProfileUpdateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=160)
    profile: dict[str, Any]


class AnalyticsRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=160)
    post_type: str = Field(min_length=1, max_length=50)
    likes: int = Field(ge=0)
    comments: int = Field(ge=0)
    shares: int = Field(ge=0)
    posted_at: datetime | None = None


PROFILE_FIELDS = (
    "niche",
    "goals",
    "audience_preferences",
    "best_performing_formats",
    "best_posting_times",
    "learned_insights",
)
PROFILE_MARKER = re.compile(r"<!--\s*INFLUX_PROFILE\s*:\s*(\{.*?\})\s*-->", re.DOTALL | re.IGNORECASE)


def profile_connection() -> sqlite3.Connection:
    """Open the small local store used to retain a creator's durable profile."""
    PROFILE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(PROFILE_DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE IF NOT EXISTS creator_profiles (
        user_id TEXT PRIMARY KEY,
        profile_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
        )"""
    )
    return connection


def load_user_profile(user_id: str) -> dict[str, str]:
    with profile_connection() as connection:
        row = connection.execute("SELECT profile_json FROM creator_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return {}
    try:
        profile = json.loads(row["profile_json"])
    except (TypeError, json.JSONDecodeError):
        return {}
    return {field: value for field, value in profile.items() if field in PROFILE_FIELDS and isinstance(value, str) and value.strip()}


def save_user_profile(user_id: str, updates: dict[str, Any]) -> dict[str, str]:
    profile = load_user_profile(user_id)
    for field in PROFILE_FIELDS:
        value = updates.get(field)
        if isinstance(value, str) and value.strip():
            profile[field] = value.strip()[:2_000]
    if profile:
        with profile_connection() as connection:
            connection.execute(
                """INSERT INTO creator_profiles (user_id, profile_json, updated_at) VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET profile_json = excluded.profile_json, updated_at = excluded.updated_at""",
                (user_id, json.dumps(profile), datetime.now(timezone.utc).isoformat()),
            )
    return profile


def user_profile_updated_at(user_id: str) -> str | None:
    with profile_connection() as connection:
        row = connection.execute("SELECT updated_at FROM creator_profiles WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    try:
        updated_at = datetime.fromisoformat(row["updated_at"])
    except (TypeError, ValueError):
        return None
    return updated_at.strftime("%b %d, %Y at %H:%M UTC")


def extract_profile_update(reply: str) -> tuple[str, dict[str, Any]]:
    """Remove the model-only profile marker before a reply is returned to the client."""
    match = PROFILE_MARKER.search(reply)
    if not match:
        return reply, {}
    try:
        update = json.loads(match.group(1))
    except json.JSONDecodeError:
        update = {}
    return PROFILE_MARKER.sub("", reply).strip(), update if isinstance(update, dict) else {}


def profile_for_dashboard(profile: dict[str, str], updated_at: str | None) -> dict[str, str]:
    return {
        "audience": profile.get("audience_preferences", "Not learned yet"),
        "niche": profile.get("niche", "Not learned yet"),
        "posting_time": profile.get("best_posting_times", "Not learned yet"),
        "tone": "Not learned yet",
        "language": "Not learned yet",
        "preferred_format": profile.get("best_performing_formats", "Not learned yet"),
        "last_updated": updated_at or "Not learned yet",
        "summary": profile.get("learned_insights") or profile.get("goals", "No creator preferences have been learned yet."),
    }


def headers(token: str | None) -> dict[str, str]:
    result = {"Content-Type": "application/json"}
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def external_error(name: str, detail: str, status_code: int = 503) -> HTTPException:
    return HTTPException(status_code=status_code, detail=f"{name}: {detail}")


def gateway_error_detail(response: httpx.Response) -> str:
    """Extract OpenClaw's API error without logging tokens or message contents."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:500] or f"HTTP {response.status_code}"
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and isinstance(error.get("message"), str):
        return error["message"][:500]
    if isinstance(error, str):
        return error[:500]
    return json.dumps(body)[:500]


async def hindsight_request(method: str, path: str, **kwargs: Any) -> Any:
    if not HINDSIGHT_TOKEN:
        raise external_error("Hindsight Cloud is not configured", "Set HINDSIGHT_API_TOKEN in backend/.env.")
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.request(method, f"{HINDSIGHT_URL}{path}", headers=headers(HINDSIGHT_TOKEN), **kwargs)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        raise external_error("Hindsight Cloud request failed", exc.response.text[:500], exc.response.status_code) from exc
    except httpx.HTTPError as exc:
        raise external_error("Hindsight Cloud is unavailable", str(exc)) from exc


async def memory_items(limit: int = 100) -> dict[str, Any]:
    records = await hindsight_request("GET", f"/v1/default/banks/{HINDSIGHT_BANK_ID}/memories/list", params={"limit": min(max(limit, 1), 100)})
    if not isinstance(records, dict):
        raise external_error("Hindsight Cloud returned an invalid memory response", "Expected an object.", 502)
    return records


PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "audience": {"type": "string"},
        "niche": {"type": "string"},
        "posting_time": {"type": "string"},
        "tone": {"type": "string"},
        "language": {"type": "string"},
        "preferred_format": {"type": "string"},
        "last_updated": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["audience", "niche", "posting_time", "tone", "language", "preferred_format", "last_updated", "summary"],
    "additionalProperties": False,
}


async def creator_profile() -> dict[str, str]:
    """Ask Hindsight to synthesize its current memory, rather than parsing user facts in this app."""
    question = (
        "Create the current creator profile from durable memories only. "
        "For audience, niche, posting_time, tone, language, and preferred_format, "
        "use the newest explicit preference if memories conflict. Use 'Not learned yet' "
        "when the memory bank has no reliable value. Include a concise summary and last_updated."
    )
    data = await hindsight_request(
        "POST",
        f"/v1/default/banks/{HINDSIGHT_BANK_ID}/reflect",
        json={"query": question, "budget": "low", "max_tokens": 400, "response_schema": PROFILE_SCHEMA},
    )
    structured = data.get("structured_output")
    if isinstance(structured, str):
        try:
            structured = json.loads(structured)
        except json.JSONDecodeError:
            structured = None
    if isinstance(structured, dict):
        return {key: str(structured.get(key, "Not learned yet")) for key in PROFILE_SCHEMA["properties"]}
    return {key: "Not learned yet" for key in PROFILE_SCHEMA["properties"]}


def analytics_entry(item: dict[str, Any], user_id: str) -> dict[str, Any] | None:
    metadata = item.get("metadata") or {}
    # Records created before user IDs were introduced belong to the current local workspace.
    if metadata.get("source") not in ANALYTICS_SOURCES or metadata.get("user_id") not in (None, user_id):
        return None
    try:
        likes, comments, shares = (int(metadata[name]) for name in ("likes", "comments", "shares"))
    except (KeyError, TypeError, ValueError):
        return None
    return {
        "id": item.get("id") or item.get("memory_id") or item.get("document_id"),
        "post_type": metadata.get("post_type", "Unknown"),
        "likes": likes, "comments": comments, "shares": shares,
        "total_engagement": likes + comments + shares,
        "posted_at": metadata.get("posted_at") or item.get("created_at") or item.get("mentioned_at"),
    }


def analytics_profile_update(summary: dict[str, Any]) -> dict[str, str]:
    """Promote calculated analytics into the same durable profile used by chat."""
    if not summary.get("total_entries") or not summary.get("best_format"):
        return {}
    return {
        "best_performing_formats": str(summary["best_format"]),
        "learned_insights": str(summary["insight"]),
    }


async def sync_analytics_profile(user_id: str) -> None:
    """Refresh profile insights before a chat without making chat depend on analytics availability."""
    try:
        records = await memory_items()
    except HTTPException as exc:
        logger.info("analytics_profile_sync_skipped user_id=%s detail=%s", user_id, exc.detail)
        return
    raw_items = records.get("items", [])
    if not isinstance(raw_items, list):
        return
    entries = [entry for item in raw_items if isinstance(item, dict) and (entry := analytics_entry(item, user_id)) is not None]
    save_user_profile(user_id, analytics_profile_update(analytics_summary(entries)))


def analytics_summary(entries: list[dict[str, Any]]) -> dict[str, Any]:
    if not entries:
        return {"total_entries": 0, "average_engagement": 0, "best_format": None, "format_averages": {}, "insight": "Log your first post to generate a personalized insight."}
    grouped: dict[str, list[int]] = defaultdict(list)
    for entry in entries:
        grouped[entry["post_type"]].append(entry["total_engagement"])
    averages = {name: round(sum(values) / len(values), 1) for name, values in grouped.items()}
    best = max(averages, key=averages.get)
    runner_up = max((value for name, value in averages.items() if name != best), default=0)
    comparison = round(averages[best] / runner_up, 1) if runner_up else None
    insight = f"{best} is currently your strongest format with {averages[best]} average engagements."
    if comparison and comparison > 1:
        insight += f" That is {comparison}× the next-best format."
    return {
        "total_entries": len(entries),
        "average_engagement": round(sum(entry["total_engagement"] for entry in entries) / len(entries), 1),
        "best_format": best,
        "format_averages": averages,
        "comparison_multiplier": comparison,
        "insight": insight,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "llm": "Groq gpt-oss-120b via OpenClaw", "memory": "Hindsight Cloud"}


@app.post("/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest) -> ChatResponse:
    """Reply with the creator's persisted profile available in every conversation."""

    if not GATEWAY_TOKEN:
        raise external_error("OpenClaw Gateway is not configured", "Set OPENCLAW_GATEWAY_TOKEN in backend/.env.")
    if not GATEWAY_MODEL:
        raise external_error("OpenClaw Gateway is not configured", "Set OPENCLAW_MODEL in backend/.env.")

    await sync_analytics_profile(payload.user_id)
    profile = load_user_profile(payload.user_id)
    missing_profile_fields = [field.replace("_", " ") for field in PROFILE_FIELDS if not profile.get(field)]
    body = {
        "model": GATEWAY_MODEL,
        "user": f"conv:{payload.conversation_id}",
        "stream": False,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Influx.AI, an AI Social Media Engagement Agent. "
                    "The OpenClaw 'main' agent automatically recalls relevant "
                    "Hindsight memories before every response. Treat recalled "
                    "memories as the latest truth unless the user explicitly "
                    "changes them. Give actionable, platform-specific advice. "
                    "Default to a concise Markdown answer with 3–5 key points, "
                    "short paragraphs, and only the details needed to act. "
                    "Provide a complete, detailed answer when the user explicitly "
                    "asks for one. Use standard Markdown only: never output HTML tags "
                    "such as <br>, and do not put social-media recommendations or "
                    "checklists in code fences. Use headings, lists, and tables normally. "
                    f"The saved creator profile for this user is: {json.dumps(profile) or '{}'} . "
                    f"Missing profile details are: {', '.join(missing_profile_fields) or 'none'}. "
                    "When details needed for useful advice are missing, ask for one or two "
                    "of them naturally. At the very end of every response, append one hidden "
                    "HTML comment exactly in this format: <!-- INFLUX_PROFILE: {\"field\": \"value\"} -->. "
                    "Only include fields explicitly stated or corrected by the user in this turn; "
                    "otherwise use {}. Valid fields are niche, goals, audience_preferences, "
                    "best_performing_formats, best_posting_times, and learned_insights."
                ),
            },
            {
                "role": "user",
                "content": payload.message,
            },
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10)) as client:
            response = await client.post(
                f"{GATEWAY_URL}/v1/chat/completions",
                headers=headers(GATEWAY_TOKEN),
                json=body,
            )
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPStatusError as exc:
        detail = gateway_error_detail(exc.response)
        logger.warning(
            "gateway_chat_failed status=%s model=%s conversation_id=%s detail=%s",
            exc.response.status_code,
            GATEWAY_MODEL,
            payload.conversation_id,
            detail,
        )
        raise external_error(
            "OpenClaw Gateway request failed",
            detail,
            exc.response.status_code,
        ) from exc

    except httpx.HTTPError as exc:
        logger.warning(
            "gateway_chat_unavailable model=%s conversation_id=%s error=%s",
            GATEWAY_MODEL,
            payload.conversation_id,
            str(exc),
        )
        raise external_error(
            "OpenClaw Gateway is unavailable",
            str(exc),
        ) from exc

    try:
        reply = data["choices"][0]["message"]["content"]

    except (KeyError, IndexError, TypeError) as exc:
        raise external_error(
            "OpenClaw Gateway returned an invalid chat response",
            str(exc),
            502,
        ) from exc

    if not isinstance(reply, str):
        raise external_error("OpenClaw Gateway returned an invalid chat response", "Reply content was not text.", 502)
    reply, profile_update = extract_profile_update(reply)
    save_user_profile(payload.user_id, profile_update)
    return ChatResponse(
        reply=reply,
        conversation_id=payload.conversation_id,
    )


@app.get("/memory")
async def memory(user_id: str) -> dict[str, Any]:
    records = await memory_items()
    profile = profile_for_dashboard(load_user_profile(user_id), user_profile_updated_at(user_id))
    items = records.get("items", [])
    if not isinstance(items, list):
        items = []
    analytics_count = sum(1 for item in items if isinstance(item, dict) and (item.get("metadata") or {}).get("source") in ANALYTICS_SOURCES)
    latest = items[0] if items else None
    return {"count": records.get("total", len(items)), "profile": profile, "analytics_count": analytics_count, "latest_memory": latest, "items": items}


@app.post("/profile")
async def update_profile(payload: ProfileUpdateRequest) -> dict[str, Any]:
    """Accept a recovered profile marker from an older locally saved conversation."""
    return {"profile": save_user_profile(payload.user_id, payload.profile)}


@app.get("/analytics")
async def analytics(user_id: str) -> dict[str, Any]:
    records = await memory_items()
    raw_items = records.get("items", [])
    entries = [entry for item in raw_items if isinstance(item, dict) and (entry := analytics_entry(item, user_id)) is not None] if isinstance(raw_items, list) else []
    entries.sort(key=lambda entry: str(entry.get("posted_at") or ""), reverse=True)
    summary = analytics_summary(entries)
    save_user_profile(user_id, analytics_profile_update(summary))
    return {"items": entries, "summary": summary}


@app.post("/analytics", status_code=status.HTTP_201_CREATED)
async def add_analytics(payload: AnalyticsRequest) -> dict[str, Any]:
    posted_at = (payload.posted_at or datetime.now(timezone.utc)).isoformat()
    content = f"Creator analytics: {payload.post_type}; {payload.likes} likes, {payload.comments} comments, {payload.shares} shares; total engagement {payload.likes + payload.comments + payload.shares}."
    await hindsight_request(
        "POST",
        f"/v1/default/banks/{HINDSIGHT_BANK_ID}/memories",
        json={"items": [{"content": content, "document_id": f"influx-ai-analytics-{uuid4()}", "metadata": {"source": "influx-ai-analytics", "user_id": payload.user_id, "post_type": payload.post_type, "likes": str(payload.likes), "comments": str(payload.comments), "shares": str(payload.shares), "posted_at": posted_at}}]},
    )
    return {"status": "stored", "message": "Analytics saved to Hindsight Cloud."}
