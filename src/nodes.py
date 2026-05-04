from langchain_core.messages import SystemMessage, AIMessage
from typing import Any, Dict
from agents import Runner

from models.state import State
from agents_folder.filter_agent import filter_agent
from agents_folder.lookup_agent import lookup_agent
from agents_folder.conversation_agent import conversation_agent

class Nodes:
    def __init__(self):
      
        self.model = "gpt-4o-mini"

    async def filter_node(self, state: State) -> State:
        """ Runs the FilterAgent to filter messages """

        result = await Runner.run(
            filter_agent,
            state["query"],
            metadata={
                "langgraph_run_id": state["run_id"],
                "node": "Filter"
            }
        )

        state.filter_validation = result.valid_response
        state.filter_classification = result.message_type

        if not state.filter_validation:
            # state.messages.append({"role":"assistant","content":"Could not find information about this query. Please ask something again."})
            state.messages.append({"role":"assistant","content":result.message_for_user})

        return state

    async def lookup_node(self, state: State) -> State:
        """ To be defined """

        lookup_output = await Runner.run(
            lookup_agent,
            state["query"],
            metadata={
                "langgraph_run_id": state["run_id"],
                "node": "Lookup"
            }
        )

        state.relevant_documents = lookup_output.output
        state.found_information = lookup_output.found_information
        return state

    async def conversation_node(self, state: State) -> State:  
        """ To be defined """ 

        result = await Runner.run(
            conversation_agent,
            state["query"],
            state["messages"],
            state["relevant_documents"],
            metadata={
                "langgraph_run_id": state["run_id"],
                "node": "Conversation"
            }
        )

        state.messages.append(result.final_output)

        return state
        