from langchain_core.messages import SystemMessage, AIMessage
from typing import Any, Dict
from agents import RunConfig, Runner

from models.state import State
from agents_folder.filter_agent import filter_agent
from agents_folder.lookup_agent import lookup_agent, search_knowledge_base_impl
from agents_folder.conversation_agent import conversation_agent

class Nodes:
    def __init__(self):
      
        self.model = "gpt-4o-mini"

    async def filter_node(self, state: State) -> State:
        """ Runs the FilterAgent to filter messages """

        result = await Runner.run(
            filter_agent,
            input=f"""
            User query: {state.query}
            
            History of messages: {state.messages}
            """
        )

        state.filter_validation = result.final_output.valid_response
        state.filter_classification = result.final_output.message_type
        state.translated_query = result.final_output.translated_query

        if not state.filter_validation:
            # state.messages.append({"role":"assistant","content":"Could not find information about this query. Please ask something again."})
            state.messages.append({"role":"assistant","content":result.final_output.message_for_user})

        return state

    async def conversation_node(self, state: State) -> State:  
        """ Use the information provided in the steps before to answer the user's query """ 

        if state.filter_classification == "info":
            documents = search_knowledge_base_impl(state.translated_query)

            if documents:
                state.relevant_documents.extend(documents)

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
        