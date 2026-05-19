import uuid
import asyncio
from fastapi import FastAPI, Request
from pydantic import BaseModel
import httpx
import os

from career_conversation_chatbot import ChatbotService

app = FastAPI()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

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

@app.post("/chat")
async def chat(req: ChatRequest):

    bot = await get_or_create_session(req.user_id)

    # history is empty for now (we improve later)
    history = []

    reply = await bot.chat(req.message, history)

    return {
        "user_id": req.user_id,
        "reply": reply["content"]
    }

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    text = message.get("text")

    if not chat_id or not text:
        return {"ok": True}

    bot = await get_or_create_session(chat_id)

    history = []  # later you can persist this per user

    reply = await bot.chat(text, history)

    await send_telegram_message(chat_id, reply["content"])

    return {"ok": True}


async def send_telegram_message(chat_id: str, text: str):
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            }
        )