import os
import requests
from pydantic import BaseModel, Field
from typing import Dict, Literal, Optional
from agents import Agent, ModelSettings
from dotenv import load_dotenv

from agents_folder.filter_agent import filter_agent, FilteredResponse
from agents_folder.lookup_agent import lookup_agent
from agents_folder.conversation_agent import conversation_agent

load_dotenv(override=True)

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""You are rounting agent acting on behalf of Andreu Otega.
The user will make queries about Andreu's professional career, studies, personal information and hobbies. The user also may want to be contacted by Andreu Ortega.

You MUST follow the workflow strictly and follow the routing described in the steps.

Workflow:

    Step 1: Use the 'FilterTool' tool to do a first check on the received query (use the query exactly as it is).
        Based on the 'FilterTool' output (do not reinterpret anything):
        - If you have do not have a valid response, then go to Step 2.
        - If you have a valid response and the message_type type is and ONLY is 'info', then go to Step 3.
        - If you have a valid response and the message_type is and ONLY is 'contact', then go to Step 4. 

        You cannot repeat Step 1 and either have to choose Step 2, Step 3 or Step 4.

    Step 2: The workflow TERMINATES and no further steps are allowed. The final answer must explain, as if would be Andreu in first person, that the chatbot is just inteded for answering queries about yourself and ask the user to query again.
    Step 3: Use the 'LookUpTool' to retrieve the most important documents related with the user query. Then go to step 4.
    Step 4: Use the initial query to call the 'ConversationTool' tool to produce the final answer to the user's query.

Important rules:
- The model may only call tools if the workflow step explicitly AND unambiguously requires it AND all required fields are present. If not stated in the step you are currently doing, DO NOT call the tool.
- Do not skip any state unless mentioned in the workflow.
"""

class RouterDecision(BaseModel):
    step: Literal["1", "2", "3", "4", "END"] = Field(description="To indicate the step decided to do")
    reasoning: str = Field(description="Describes the reason of being in the current step")
    final_answer: str = Field(description="Final answer of the workflow, which will be used to answer the user's query")
    filter_tool_output: Optional[FilteredResponse] = Field(description="Output of the 'FilterTool' tool")

filter_tool = filter_agent.as_tool(tool_name="FilterTool", tool_description="Tool to filter if query should be admitted or not")
lookup_tool = lookup_agent.as_tool(tool_name="LookupTool", tool_description="Tool to search in the RAG database the most important documents related with the query")
conversation_tool = conversation_agent.as_tool(tool_name="ConversationTool", tool_description="Tool to formulate an answer to the query based in the documents provided")

router_tools = [filter_tool, lookup_tool, conversation_tool]

router_agent = Agent(
    name="RouterAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=router_tools,
    model_settings=ModelSettings(tool_choice="required"),
)