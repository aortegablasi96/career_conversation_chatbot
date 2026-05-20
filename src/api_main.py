import uuid
import asyncio
from fastapi import FastAPI, Request, BackgroundTasks
from pydantic import BaseModel
import httpx
import os

from career_conversation_chatbot import ChatbotService
from resources.start_messages import START_MESSAGES

app = FastAPI()

processed_updates = set()
chat_histories: dict[str, list[dict]] = {}
MAX_MESSAGES = 20

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
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    background_tasks.add_task(process_telegram_update, data)

    return {"ok": True}

async def process_telegram_update(data: dict):

    update_id = data.get("update_id")
    if update_id in processed_updates:
        return
    processed_updates.add(update_id)

    message = data.get("message", {})
    language_code = message.get("from", {}).get("language_code", "en")
    chat = message.get("chat", {})
    chat_id = str(chat.get("id"))
    text = message.get("text")

    if not chat_id or not text:
        return {"ok": True}

    history = chat_histories.get(chat_id, [])

    bot = await get_or_create_session(chat_id)

    if text.strip().lower() == "/start":
        lang = language_code.lower().split("-")[0]
        start_text = START_MESSAGES.get(lang, START_MESSAGES["en"])

        await send_telegram_message(chat_id, start_text)

        return
    
    reply = await bot.chat(text, history)

    history.extend([
        {
            "role": "user",
            "content": text
        },
        {
            "role": "assistant",
            "content": reply["content"]
        }
    ])
            
    chat_histories[chat_id] = history[-MAX_MESSAGES:]

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