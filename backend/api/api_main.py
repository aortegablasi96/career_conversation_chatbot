import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chatbot import router as chatbot_router
from api.routes.telegram import router as telegram_router
from api.routes.app import router as app_router


async def _register_telegram_webhook() -> None:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        return
    # RENDER_EXTERNAL_URL is injected automatically by Render on all plans.
    # Set TELEGRAM_WEBHOOK_URL to override (useful for local ngrok tunnels).
    base_url = os.getenv("TELEGRAM_WEBHOOK_URL") or os.getenv("RENDER_EXTERNAL_URL")
    if not base_url:
        print("TELEGRAM: skipping webhook registration — no base URL configured")
        return
    webhook_url = f"{base_url.rstrip('/')}/telegram/webhook"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={"url": webhook_url},
        )
    result = resp.json()
    if result.get("ok"):
        print(f"TELEGRAM: webhook registered → {webhook_url}")
    else:
        print(f"TELEGRAM: webhook registration failed — {result}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _register_telegram_webhook()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://career-conversation-chatbot.onrender.com",
        "https://career-conversation-chatbot.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot_router)
app.include_router(telegram_router)
app.include_router(app_router)