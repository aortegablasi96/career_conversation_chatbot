import os
import requests
from pydantic import BaseModel, Field
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
You role is to execute the following flow, step by step, using the agent-as-tools provided only when specified:

    1. Use the 'FilterTool' tool to do a first check on the received query.
        You MUST use ONLY the output of Step 1 (FilterTool):
            - response (bool)
            - user_details (object or None)
            - message_type ("info" or "contact" or None)

        DO NOT re-interpret the user message.

        Routing rules:
            
            IF response == False:
                → go to Step 1.1
            
            IF response == True AND message_type == "info":
                → go to Step 3

            IF response == True AND message_type == "contact" and user_details is None:
                → go to Step 2.1
            
            IF response == True AND message_type == "contact" user_details is not None:
                → go to Step 2.2

    1.1. The workflow TERMINATES and no further steps are allowed. The output should explain, as if would be Andreu in first person, that the chatbot is just inteded for answering queries about yourself and ask the user to query again.
    2.1 The workflow TERMINATES and no further steps are allowed.. Ask for the user details (name, mail and ask why he wants to be contacted).
    2.2 Use the 'RecordUserDetailsTool' tool to send a push notification. The workflow TERMINATES and no further steps are allowed.
    3. Use the 'LookUpTool' to retrieve the most important documents related with the user query. If you obtain information, go to the step 4.1, otherwise go to the step 4.2.
    4.1. Use the documents obtained in the last step in the 'ConversationTool' tool to produce an answer to the user's query based on the documents given to the tool.
    4.2. Use the 'RecordQuestionsTool' tool to send a push notification with the uknown user's query.

Output the response obtained from the last step as it is. 

Routing rules:
- The model may only call tools if the workflow step explicitly AND unambiguously requires it AND all required fields are present. If not stated in the step you are currently doing, DO NOT call the tool.
- Never skip any step of the workflow unless indicated in the step's description.
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

class RecordDetailsInput(BaseModel):
    email: str = Field(description="User email")
    name: str = Field(description="User name", default="Name not provided") 
    notes: str = Field(description="User additional notes", default="not provided")

@function_tool(name_override="RecordUserDetailsTool")
def record_user_details(payload: RecordDetailsInput) -> Dict[str, str]:
    """ Send a push notification with the user's information """
    
    push(f"Career conversation agent - Recording contact details of interested user: {payload.name} with email {payload.email} and notes {payload.notes}")
    return {"recorded": "ok"}

class RecordUnknownQuestionInput(BaseModel):
    query: str = Field(description="Query to be sent as push notification")

@function_tool(name_override="RecordQuestionsTool")
def record_unknown_question(payload: RecordUnknownQuestionInput) -> Dict[str, str]:
    """ Send a push notification with the unkown query """

    push(f"Career Conversation Agent - Recording unknown question: {payload.query}")
    return {"recorded": "ok"}

filter_tool = filter_agent.as_tool(tool_name="FilterTool", tool_description="Tool to filter if query should be admitted or not")
lookup_tool = lookup_agent.as_tool(tool_name="LookupTool", tool_description="Tool to search in the RAG database the most important documents related with the query")
conversation_tool = conversation_agent.as_tool(tool_name="ConversationTool", tool_description="Tool to formulate an answer to the query based in the documents provided")

router_tools = [filter_tool, lookup_tool, conversation_tool, record_unknown_question,record_user_details]

router_agent = Agent(
    name="RouterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=router_tools,
    model_settings=ModelSettings(tool_choice="required")
)