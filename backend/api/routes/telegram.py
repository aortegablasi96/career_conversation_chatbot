import os
import traceback
from collections import deque
import httpx
from fastapi import APIRouter, Request, BackgroundTasks

from resources.start_messages import START_MESSAGES
import api.routes.chatbot as chatbot_route

router = APIRouter(prefix="/telegram")

MAX_MESSAGES = 20

BOT_TOKEN = os.getenv("BOT_TOKEN")
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Bounded deque prevents unbounded memory growth from accumulated update IDs
processed_updates: deque = deque(maxlen=1000)
chat_histories: dict[str, list[dict]] = {}

@router.post("/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()

    background_tasks.add_task(process_telegram_update, data)

    return {"ok": True}

async def process_telegram_update(data: dict):
    try:
        update_id = data.get("update_id")
        if update_id in processed_updates:
            return
        processed_updates.append(update_id)

        message = data.get("message", {})
        language_code = message.get("from", {}).get("language_code", "en")
        chat = message.get("chat", {})
        chat_id = str(chat.get("id"))
        text = message.get("text")

        if not chat_id or not text:
            return {"ok": True}

        if text.strip().lower() == "/start":
            lang = language_code.lower().split("-")[0]
            start_text = START_MESSAGES.get(lang, START_MESSAGES["en"])
            await send_telegram_message(chat_id, start_text)
            return

        history = chat_histories.get(chat_id, [])

        # Append user message before calling chat so the bot sees the full history
        history = history + [{"role": "user", "content": text}]

        if not chatbot_route.engine_ready:
            await send_telegram_message(chat_id, "The assistant is still starting up. Please try again in a moment.")
            return

        reply = await chatbot_route.engine.chat(text, history)

        history.append({"role": "assistant", "content": reply})
        chat_histories[chat_id] = history[-MAX_MESSAGES:]

        await send_telegram_message(chat_id, reply)

        return {"ok": True}
    except Exception as e:
        print("TELEGRAM ERROR:", e)
        traceback.print_exc()


async def send_telegram_message(chat_id: str, text: str):

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text
            }
        )