from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes.chatbot import router as chatbot_router
from api.routes.telegram import router as telegram_router
from api.routes.app import router as app_router

app = FastAPI()

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