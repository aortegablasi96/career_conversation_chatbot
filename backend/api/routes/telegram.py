import html as html_module
import os
import re
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


def _md_to_html(text: str) -> str:
    """Convert common LLM Markdown to Telegram-safe HTML."""
    # 1. Lift out fenced code blocks so their content isn't touched by later steps.
    blocks: list[str] = []
    def _save_block(m: re.Match) -> str:
        blocks.append(f"<pre><code>{html_module.escape(m.group(2))}</code></pre>")
        return f"\x00B{len(blocks) - 1}\x00"
    text = re.sub(r"```(\w*)\n?(.*?)```", _save_block, text, flags=re.DOTALL)

    # 2. Lift out inline code spans.
    spans: list[str] = []
    def _save_span(m: re.Match) -> str:
        spans.append(f"<code>{html_module.escape(m.group(1))}</code>")
        return f"\x00S{len(spans) - 1}\x00"
    text = re.sub(r"`([^`\n]+)`", _save_span, text)

    # 3. Escape HTML special chars in the remaining plain text.
    text = html_module.escape(text)

    # 4. Convert Markdown lists to bullet characters (Telegram HTML has no <ul>/<li>).
    def _list_line(line: str) -> str:
        m = re.match(r"^([ \t]*)[-*+][ \t]+(.+)$", line)
        if m:
            level = len(m.group(1).expandtabs(2)) // 2
            return "  " * level + "• " + m.group(2)
        m = re.match(r"^([ \t]*)(\d+)\.[ \t]+(.+)$", line)
        if m:
            level = len(m.group(1).expandtabs(2)) // 2
            return "  " * level + m.group(2) + ". " + m.group(3)
        return line
    text = "\n".join(_list_line(line) for line in text.split("\n"))

    # 5. Apply inline formatting (order matters: bold before italic).
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
    text = re.sub(r"__(.+?)__", r"<u>\1</u>", text, flags=re.DOTALL)
    text = re.sub(r"_(.+?)_", r"<i>\1</i>", text)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text, flags=re.DOTALL)

    # 6. Convert headings to bold lines.
    text = re.sub(r"^#{1,6}\s+(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)

    # 7. Restore protected blocks and spans.
    for i, block in enumerate(blocks):
        text = text.replace(f"\x00B{i}\x00", block)
    for i, span in enumerate(spans):
        text = text.replace(f"\x00S{i}\x00", span)

    return text


async def send_telegram_message(chat_id: str, text: str):
    html_text = _md_to_html(text)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": html_text, "parse_mode": "HTML"},
        )
        # Fall back to plain text if Telegram rejects the HTML (e.g. unclosed tags).
        if not resp.json().get("ok"):
            await client.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )