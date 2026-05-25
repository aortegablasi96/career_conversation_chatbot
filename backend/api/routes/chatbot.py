import uuid
from pydantic import BaseModel
from fastapi import APIRouter

from app.career_conversation_chatbot import ChatbotService

router = APIRouter()

# simple in-memory session store (we improve later)
sessions = {}

async def get_or_create_session(user_id: str):
    if user_id not in sessions:
        trace_id = str(uuid.uuid4())
        sessions[user_id] = ChatbotService(trace_id)
        await sessions[user_id].setup()

    return sessions[user_id]

class ChatRequest(BaseModel):
    user_id: str
    message: str

@router.post("/chat")
async def chat(req: ChatRequest):

    bot = await get_or_create_session(req.user_id)

    history = []

    reply = await bot.chat(req.message, history)

    return {
        "user_id": req.user_id,
        "reply": reply
    }