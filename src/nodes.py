from langchain_core.messages import SystemMessage, AIMessage
from typing import Any, Dict
from agents import RunConfig, Runner

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
            state.query
        )

        state.filter_validation = result.final_output.valid_response
        state.filter_classification = result.final_output.message_type

        if not state.filter_validation:
            # state.messages.append({"role":"assistant","content":"Could not find information about this query. Please ask something again."})
            state.messages.append({"role":"assistant","content":result.final_output.message_for_user})

        return state

    async def lookup_node(self, state: State) -> State:
        """ To be defined """

        lookup_output = await Runner.run(
            lookup_agent,
            state.query
        )

        if lookup_output.final_output.output:
            state.relevant_documents.extend(lookup_output.final_output.output)
        state.found_information = lookup_output.final_output.found_information
        
        return state

    async def conversation_node(self, state: State) -> State:  
        """ To be defined """ 

        result = await Runner.run(
            conversation_agent,
            input=f"""
            User query: {state.query}

            Relevant documents: {state.relevant_documents} 
            
            History of messages: {state.messages}
            """
        )

        state.messages.append({"role":"assistant","content":result.final_output})

        return state
        