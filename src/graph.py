from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from PIL import Image
import io
import asyncio
import os
from dotenv import load_dotenv

from models.state import State
from nodes import Nodes

load_dotenv(override=True)

class Graph:
    def __init__(self,trace_id=None) -> None:
        self.trace_id = trace_id
        self.memory = MemorySaver()     
        self.nodes = Nodes()
        self.graph = None
    
    async def setup(self):
        await self.build_graph()

    async def build_graph(self):
        # Set up Graph Builder with State
        graph_builder = StateGraph(State)

        # Add nodes
        graph_builder.add_node("filter", self.nodes.filter_node)
        graph_builder.add_node("lookup",self.nodes.lookup_node)
        graph_builder.add_node("conversation", self.nodes.conversation_node)

        # Add edges
        graph_builder.add_edge(START,"filter")
        graph_builder.add_conditional_edges("filter",self.filter_router, {"lookup":"lookup","conversation":"conversation","END":END})
        graph_builder.add_conditional_edges("lookup",self.lookup_router, {"conversation":"conversation","END":END})
        graph_builder.add_edge("conversation",END)

        # Compile the graph
        self.graph = graph_builder.compile(checkpointer=self.memory)

    def filter_router(self, state:State) -> str:
        """ To be defined """

        if not state.filter_validation:
            return "END"
        elif state.filter_classification == "info":
            return "lookup"
        elif state.filter_classification == "contact":
            return "conversation"

    def lookup_router(self, state:State) -> str:
        """ To be defined """

        if state.found_information:
            return "conversation"
        else:
            return "END"

    async def run_superstep(self, message, history):
        """Run one conversation turn: user message -> filter review -> documents lookup -> generate response """
        
        if self.trace_id:
            config = {"configurable": {"thread_id": self.trace_id}}

            state = {
                "query": message,
                "messages": history,
                "filter_validation": False,
                "filter_classification": None,
                "found_information": False,
                "relevant_documents":[], 
                "translated_query": "",
                "trace_id":self.trace_id            
            }

            result = await self.graph.ainvoke(state, config=config)
        
        else:
            state = {
                "query": message,
                "messages": history,
                "filter_validation": False,
                "filter_classification": None,
                "found_information": False,
                "relevant_documents":[], 
                "translated_query": "",
                "trace_id":None 
            }

            result = await self.graph.ainvoke(state)

        # user = {"role": "user", "content": message}
        reply = result["messages"][-1]

        return reply

    def get_nodes_diagram(self):
        """ Create an image of the Graph diagram."""
        return Image.open(io.BytesIO(self.graph.get_graph().draw_mermaid_png()))