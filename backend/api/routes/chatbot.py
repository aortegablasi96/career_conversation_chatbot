import uuid
import asyncio
import time
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from cachetools import TTLCache

from app.career_conversation_chatbot import ChatbotService

router = APIRouter()

# -----------------------------
# GLOBAL STATE (engine-level)
# -----------------------------
engine = None
engine_ready = False
engine_lock = asyncio.Lock()

# -----------------------------
# USER SESSIONS (lightweight, TTL-evicted)
# max 500 concurrent users, sessions expire after 1 hour of inactivity
# -----------------------------
sessions: TTLCache = TTLCache(maxsize=500, ttl=3600)

# -----------------------------
# RATE LIMITING
# max 20 requests per user per minute
# -----------------------------
_rate_cache: TTLCache = TTLCache(maxsize=10000, ttl=60)

def _check_rate_limit(user_id: str, max_per_minute: int = 20) -> bool:
    bucket = f"{user_id}:{int(time.time() // 60)}"
    count = _rate_cache.get(bucket, 0)
    if count >= max_per_minute:
        return False
    _rate_cache[bucket] = count + 1
    return True

# -----------------------------
# REQUEST MODEL
# -----------------------------
class ChatRequest(BaseModel):
    user_id: str
    message: str = Field(max_length=2000)


# -----------------------------
# GLOBAL ENGINE WARMUP
# -----------------------------
async def setup_engine():
    """
    Builds LangChain / LangGraph ONLY ONCE.
    This is your expensive setup step.
    """
    global engine, engine_ready

    engine = ChatbotService("system_engine")
    await engine.setup()  # builds graph, loads tools, etc.

    engine_ready = True


async def ensure_engine_ready():
    """
    Safe warmup with concurrency protection.
    Prevents double initialization under concurrent /warmup calls.
    """
    global engine_ready

    if engine_ready:
        return

    async with engine_lock:
        if engine_ready:
            return
        await setup_engine()


# -----------------------------
# USER SESSION (lightweight)
# -----------------------------
def get_session(user_id: str):
    """
    Pure per-user state (NO graph building here).
    """
    if user_id not in sessions:
        sessions[user_id] = {
            "trace_id": str(uuid.uuid4()),
            "memory": []
        }

    return sessions[user_id]


# -----------------------------
# WARMUP ENDPOINT (FRONTEND DRIVEN)
# -----------------------------
@router.post("/warmup")
async def warmup():
    """
    Called by AppLoader before showing ChatWindow.
    Ensures engine is fully ready.
    """
    await ensure_engine_ready()

    return {"status": "ready"}


# -----------------------------
# CHAT ENDPOINT (EXECUTION ONLY)
# -----------------------------
@router.post("/chat")
async def chat(req: ChatRequest):

    if not engine_ready:
        return JSONResponse(
            status_code=503,
            content={"status": "warming_up"},
            headers={"Retry-After": "10"},
        )

    if not _check_rate_limit(req.user_id):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait before sending another message.")

    session = get_session(req.user_id)

    reply = await engine.chat(
        req.message,
        session["memory"]
    )

    return {
        "user_id": req.user_id,
        "reply": reply
    }