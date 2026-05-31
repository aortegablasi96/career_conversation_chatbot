from agents import Agent, function_tool
from pydantic import BaseModel, Field
from typing import Dict
from dotenv import load_dotenv

from integrations.pushover import push

load_dotenv(override=True)

MODEL = "gpt-4o-mini"

INSTRUCTIONS = """
You are handling a contact request for Andreu Ortega.

Your task:
- politely acknowledge the request
- ask for name, email, and reason for contact
- once you have the user details, use the 'RecordUserDetailsTool' to send a push notification
- do NOT answer technical questions
- do NOT discuss career details

Keep response short and professional.
"""

class RecordDetailsInput(BaseModel):
    email: str = Field(description="User email")
    name: str = Field(description="User name", default="Name not provided") 
    notes: str = Field(description="User additional notes", default="not provided")

@function_tool(name_override="RecordUserDetailsTool")
async def record_user_details(payload: RecordDetailsInput) -> Dict[str, str]:
    """ Send a push notification with the user's information """

    await push(f"Career conversation agent - Recording contact details of interested user: {payload.name} with email {payload.email} and notes {payload.notes}")
    return {"recorded": "ok"}

contact_agent = Agent(
    name="ContactAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=[record_user_details]
)