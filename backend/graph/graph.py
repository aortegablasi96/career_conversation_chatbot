from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from PIL import Image
import io
import asyncio
import os
from dotenv import load_dotenv

from backend.models.state import State
from backend.graph.nodes import Nodes

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
        graph_builder.add_node("invalid", self.nodes.invalid_query_node)
        graph_builder.add_node("contact", self.nodes.contact_node)
        graph_builder.add_node("info", self.nodes.conversation_node)

        # Add edges
        graph_builder.add_edge(START,"filter")
        graph_builder.add_conditional_edges("filter",self.filter_router, {"invalid":"invalid","contact":"contact","info":"info","END":END})
        graph_builder.add_edge("invalid",END)
        graph_builder.add_edge("contact",END)
        graph_builder.add_edge("info",END)

        # Compile the graph
        self.graph = graph_builder.compile(checkpointer=self.memory)

    def filter_router(self, state: State):

        if not state.filter_validation:
            return "invalid"

        if state.filter_classification == "contact":
            return "contact"

        if state.filter_classification == "info":
            return "info"

        return "invalid"

    async def run_superstep(self, message: str, history: list[dict]):
        """
        Run one conversation turn.

        Flow:
        User message
            -> Filter
            -> Routing
                -> Invalid
                -> Contact
                -> RAG conversation
        """

        config = {
            "configurable": {
                "thread_id": self.trace_id
            }
        }

        # -------------------------------------------------
        # INITIAL STATE
        # -------------------------------------------------

        state = State(
            query=message,

            messages=history[-8:],

            # FILTER
            filter_validation=False,
            filter_classification=None,
            subject_is_andreu=False,
            detected_language=None,
            is_followup=False,

            # RETRIEVAL
            retrieval_query=None,
            relevant_documents=[],

            # CONVERSATIONAL STATE
            active_topic=None,
            active_entity=None,

            # OUTPUT
            final_response=None,

            # OBSERVABILITY
            unknown_question_logged=False,
            contact_recorded=False,
            pushover_sent=False,

            trace_id=self.trace_id,
        )

        # -------------------------------------------------
        # EXECUTE GRAPH
        # -------------------------------------------------

        result = await self.graph.ainvoke(
            state.model_dump(),
            config=config,
        )

        # -------------------------------------------------
        # RETURN FINAL RESPONSE
        # -------------------------------------------------

        return result["final_response"]

    def get_nodes_diagram(self):
        """ Create an image of the Graph diagram."""
        return Image.open(io.BytesIO(self.graph.get_graph().draw_mermaid_png()))