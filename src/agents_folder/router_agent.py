import os
import requests
from pydantic import BaseModel
from typing import Dict
from agents import Agent, ModelSettings, function_tool
from dotenv import load_dotenv

from agents_folder.filter_agent import filter_agent
from agents_folder.lookup_agent import lookup_agent
from agents_folder.conversation_agent import conversation_agent

load_dotenv(override=True)

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""You are rounting agent acting on behalf of Andreu Otega.
The user will make queries about Andreu's professional career, studies and hobbies.
You role is to execute the following flow, step by step, using the agent-as-tools provided:

    1. Use the 'FilterTool' to check if the query is related with Andreu'. If the response is valid, proced with step 2, otherwise proceed to step 1.1.
    1.1. Go straight to the end without going through any other step. The output should explain, as if would be Andreu in first person, that the chatbot is just inteded for answering queries about yourself and ask the user to query again.
    2. Use the 'LookUpTool' to retrieve the most important documents related with the user query. If you obtain information, go to the step 3.1, otherwise go to the step 3.2.
    3.1. Use the documents obtained in the last step in the 'ConversationTool' to produce an answer to the user's query based on the documents given to the tool.
    3.2. Use the 'RecordQuestionsTool' to send a push notification with the uknown user's query.

Output the response obtained from the last step as it is. 
"""

def push(text):
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": os.getenv("PUSHOVER_TOKEN"),
            "user": os.getenv("PUSHOVER_USER"),
            "message": text,
        }
    )

@function_tool(name_override="RecordUserDetailsTool")
def record_user_details(email, name="Name not provided", notes="not provided") -> Dict[str, str]:
    """ Send a push notification with the user's information """
    
    push(f"Recording {name} with email {email} and notes {notes}")
    return {"recorded": "ok"}

class RouteInput(BaseModel):
    query: str

@function_tool(name_override="RecordQuestionsTool")
def record_unknown_question(payload: RouteInput) -> Dict[str, str]:
    """ Send a push notification with the unkown query """

    push(f"Unknown question from Career Conversation Agent: {payload.query}")
    return {"recorded": "ok"}

filter_tool = filter_agent.as_tool(tool_name="FilterTool", tool_description="Tool to filter if query should be admitted or not")
lookup_tool = lookup_agent.as_tool(tool_name="LookupTool", tool_description="Tool to search in the RAG database the most important documents related with the query")
conversation_tool = conversation_agent.as_tool(tool_name="ConversationTool", tool_description="Tool to formulate an answer to the query based in the documents provided")

router_tools = [filter_tool, lookup_tool, conversation_tool, record_unknown_question]

router_agent = Agent(
    name="RouterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=router_tools,
    model_settings=ModelSettings(tool_choice="required")
)