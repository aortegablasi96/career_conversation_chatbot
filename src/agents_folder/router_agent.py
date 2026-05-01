import os
import requests
from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from agents import Agent, ModelSettings, function_tool
from dotenv import load_dotenv

from agents_folder.filter_agent import filter_agent, UserDetails
from agents_folder.lookup_agent import lookup_agent
from agents_folder.conversation_agent import conversation_agent

load_dotenv(override=True)

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

STEP 1.1:
As a final answer, tell the user that you are a chatbot that only answers questions about Andreu Ortega and ask the user to query again.
TERMINATE the workflow.  

STEP 2.1:
DO NOT call any tool.
As a final answer, ask the user for name, email, and reason for contact.
TERMINATE the workflow.

STEP 2.2:
Call RecordUserDetailsTool using the user_details from FilterTool.
As final answer, Confirm the user that you will get in touch with them soon.
TERMINATE the workflow.

STEP 3:
Call LookUpTool using the user query.
If documents are found -> go to 4.1
If documents are not found -> go to 4.2

STEP 4.1:
Call ConversationTool with the retrieved documents and produce the final answer.
TERMINATE the workflow.

STEP 4.2:
Call RecordQuestionsTool with the unknown user query.
Then, as a final answer, output a short message saying you don't have that information.
TERMINATE the workflow.

IMPORTANT RULES:
- Tools may ONLY be called when explicitly required by the current step.
- After steps 1.1, 2.1, 2.2, 4.1, or 4.2 the workflow TERMINATES.
- Every time you are about to execute a step (1.1, 2.1, 2.2, 3, 4.1, 4.2),
  you MUST first output a RouterDecision JSON object indicating the step.

Output format:
1) Output RouterDecision JSON with the step you are about to execute.
"""

class RouterDecision(BaseModel):
    step: Literal["1","1.1", "2.1", "2.2", "3", "4.1", "4.2"]
    response: bool
    message_type: Optional[Literal["info", "contact"]] = None
    user_details: Optional[UserDetails] = Field(description="User contact details")
    email: Optional[str] = None
    final_answer: Optional[str] = None

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