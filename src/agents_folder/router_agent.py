import os
import requests
from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from agents import Agent, ModelSettings, Runner, function_tool
from dotenv import load_dotenv

from agents_folder.filter_agent import filter_agent, UserDetails
from agents_folder.lookup_agent import lookup_agent
from agents_folder.conversation_agent import conversation_agent

load_dotenv(override=True)

async def route(messages):
    router_result = await Runner.run(router_agent, messages)
    router_decision = router_result.final_output

    if router_decision.step == "1.1":
        return "I'm sorry, I can't answer that question."
    elif router_decision.step == "2.1":
        return "I'm sorry, I can't answer that question."
    elif router_decision.step == "2.2":
        return "I'm sorry, I can't answer that question."
    elif router_decision.step == "3":
        return "I'm sorry, I can't answer that question."

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""You are a routing agent acting on behalf of Andreu Ortega.

You MUST follow the workflow strictly and execute steps in order.
Before executing any step, you MUST first output a JSON object matching RouterDecision
showing the step you are about to execute.

Workflow:

STEP 1:
Call FilterTool on the user query.
FilterTool returns:
- response (bool)
- user_details (object or null)
- message_type ("info" or "contact" or null)

After receiving FilterTool output, decide next step ONLY using these values.
DO NOT reinterpret the user message.

Routing rules:

IF response == false:
    Next step is 1.1

IF response == true AND message_type == "contact" AND user_details is null:
    Next step is 2.1

IF response == true AND message_type == "contact" AND user_details is not null:
    Next step is 2.2

IF response == true AND message_type == "info":
    Next step is 3

IMPORTANT RULES:
- Tools may ONLY be called when explicitly required by the current step.

Output format:
1) Output RouterDecision JSON with the step you are about to execute.
"""

class RouterDecision(BaseModel):
    step: Literal["1.1", "2.1", "2.2", "3"]
    response: bool
    message_type: Optional[Literal["info", "contact"]] = None
    user_details: Optional[UserDetails] = Field(description="User contact details")

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

router_tools = [filter_tool, lookup_tool, conversation_tool, record_unknown_question, record_user_details]

router_agent = Agent(
    name="RouterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=router_tools,
    output_type=RouterDecision
)