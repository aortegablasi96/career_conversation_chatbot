from agents import Agent, ModelSettings
from dotenv import load_dotenv

from agents_folder.lookup_agent import lookup_agent
from agents_folder.conversation_agent import conversation_agent

load_dotenv(override=True)

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""You are rounting agent acting on behalf of Andreu Otega.
The user will make queries about Andreu's professional career, studies and hobbies.
You role is to execute the following flow, step by step, using the agent-as-tools provided:

    1. Use the 'LookUpTool' to retrieve the most important documents related with the user query.
    2. Use the documents obtained in the last step in the 'ConversationTool' to produce an answer to the user's query based on the documents given to the tool.

Output the response obtained from the last step as it is.
"""

lookup_tool = lookup_agent.as_tool(tool_name="LookupTool", tool_description="Tool to search in the RAG database the most important documents related with the query")
conversation_tool = conversation_agent.as_tool(tool_name="ConversationTool", tool_description="Tool to formulate an answer to the query based in the documents provided")

router_tools = [lookup_tool, conversation_tool]

router_agent = Agent(
    name="ConversationAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=router_tools,
    model_settings=ModelSettings(tool_choice="required")
)