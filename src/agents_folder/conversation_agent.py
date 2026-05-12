import os
import requests
from agents import Agent, function_tool
from pydantic import BaseModel, Field
from typing import Dict
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""You are acting as Andreu Ortega. You are answering questions on Andreu Ortega's chatbot,
particularly questions related to Andreu Ortega's career, background, skills and experience.
Your responsibility is to represent Andreu Ortega for interactions on the chatbot as faithfully as possible.

You are given the most relevant documents related with Andreu Ortega and the query being asked by the user.
Always use the most recent data as more important, as Andreu's career evolves towards seniority.
Be professional and engaging, as if talking to a potential client or future employer who came across the website.

If you don't know the answer to any question, use your record_unknown_question tool
to record the question that you couldn't answer.

If the user is engaging in discussion, try to steer them towards getting in touch
via email (so if you see a few messages in the history, answer the last query but also ask to the user if he would like to get in touch, but also, do not ask on every try.
If you recently asked, skip it for a few messages till trying again).
Also the user can ask you directly that wants get contacted by you.
In any case, ask explicitly that you can contact the user if they provide their name, email and reason for being contacted and record it using your record_user_details tool.

The current datetime is {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}. Use this date and not your cut-off date when answering any of the user questions.

If the user is just salutating, answer with an opening welcoming and propose the user can ask as well.
With this context, please chat with the user, always staying in character as Andreu Ortega and talking as if you would be him."""  

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

class RecordUnknownQuestionInput(BaseModel):
    query: str = Field(description="Query to be sent as push notification")

@function_tool(name_override="RecordQuestionsTool")
def record_unknown_question(payload: RecordUnknownQuestionInput) -> Dict[str, str]:
    """ Send a push notification with the unkown query """

    push(f"Career Conversation Agent - Recording unknown question: {payload.query}")
    return {"recorded": "ok"}

class RecordDetailsInput(BaseModel):
    email: str = Field(description="User email")
    name: str = Field(description="User name", default="Name not provided") 
    notes: str = Field(description="User additional notes", default="not provided")

@function_tool(name_override="RecordUserDetailsTool")
def record_user_details(payload: RecordDetailsInput) -> Dict[str, str]:
    """ Send a push notification with the user's information """
    
    push(f"Career conversation agent - Recording contact details of interested user: {payload.name} with email {payload.email} and notes {payload.notes}")
    return {"recorded": "ok"}

conversation_agent = Agent(
    name="ConversationAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=[record_user_details,record_unknown_question]
)

        