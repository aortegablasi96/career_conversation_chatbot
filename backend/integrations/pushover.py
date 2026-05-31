import os
import httpx
from dotenv import load_dotenv

load_dotenv(override=True)


async def push(text: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": os.getenv("PUSHOVER_TOKEN"),
                "user": os.getenv("PUSHOVER_USER"),
                "message": text,
            },
        )
