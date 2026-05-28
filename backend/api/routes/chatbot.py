import uuid
import asyncio
from pydantic import BaseModel
from fastapi import APIRouter

from app.career_conversation_chatbot import ChatbotService

router = APIRouter()

# -----------------------------
# GLOBAL STATE (engine-level)
# -----------------------------
engine = None
engine_ready = False
engine_lock = asyncio.Lock()

# -----------------------------
# USER SESSIONS (lightweight)
# -----------------------------
sessions = {}

# -----------------------------
# REQUEST MODEL
# -----------------------------
class ChatRequest(BaseModel):
    user_id: str
    message: str


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
        return {"status": "warming_up"}

    session = get_session(req.user_id)

    reply = await engine.chat(
        req.message,
        session["memory"]
    )

    return {
        "user_id": req.user_id,
        "reply": reply
    }