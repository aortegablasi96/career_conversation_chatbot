from langchain_core.messages import SystemMessage, AIMessage
from typing import Any, Dict
from agents import RunConfig, Runner

from models.state import State
from resources.invalid_messages import INVALID_MESSAGES
from agents_folder.filter_agent import filter_agent
from agents_folder.contact_agent import contact_agent
from agents_folder.query_normalizer_agent import query_normalizer_agent
from agents_folder.conversation_agent import conversation_agent, format_documents, search_knowledge_base

class Nodes:
    def __init__(self):
      
        self.model = "gpt-4o-mini"

    async def filter_node(self, state: State) -> State:

        filter_input = f"""
            LATEST USER MESSAGE:
            {state.query}

            CONVERSATION STATE:
            - active_topic: {state.active_topic}
            - active_entity: {state.active_entity}
        """

        result = await Runner.run(
            filter_agent,
            input=filter_input
        )

        output = result.final_output

        state.filter_validation = output.valid
        state.subject_is_andreu = output.subject_is_andreu
        state.filter_classification = output.classification
        state.detected_language = output.detected_language
        state.is_followup = output.is_followup
        state.active_topic = output.detected_topic
        state.active_entity = output.detected_entity

        return state

    async def invalid_query_node(self, state: State) -> State:
        """ Return fixed messages if query is fixed """

        state.final_response = INVALID_MESSAGES.get(state.detected_language, INVALID_MESSAGES["en"])

        return state

    async def contact_node(self, state: State) -> State:
        """ Ask for the contact details and send a push notification """

        recent_messages = "\n".join(
            [
                f"{m['role']}: {m['content']}"
                for m in state.messages[-5:]
            ]
        )

        contact_input = f"""
            LATEST USER MESSAGE:
            {state.query}

            DETECTED LANGUAGE:
            {state.detected_language}

            RECENT CONVERSATION HISTORY:
            {recent_messages}

            TASK:
            - Determine whether the user wants to be contacted.
            - Ask politely for missing information if needed.
            - If enough information is available, use your tool to record the contact request.
        """

        result = await Runner.run(
            contact_agent,
            contact_input
        )

        state.final_response = result.final_output
        state.contact_recorded = True
        state.pushover_sent = True

        return state

    async def conversation_node(self, state: State) -> State:  
        """ Use the information provided in the steps before to answer the user's query """

        normalizer_input = f"""
            USER QUERY:
            {state.query}

            CONVERSATION CONTEXT:
            - active_topic: {state.active_topic}
            - active_entity: {state.active_entity}
            - is_followup: {state.is_followup}

            TASK:
            Normalize and optimize the query for retrieval.
            If the query is not in English, translate it to English.
            If it is a follow-up question, preserve contextual meaning.
            Return ONLY the optimized retrieval query.
        """

        result = await Runner.run(
            query_normalizer_agent,
            normalizer_input
        )

        normalized_output = result.final_output
        state.retrieval_query = normalized_output.normalized_query

        documents = await search_knowledge_base(normalized_output, active_topic=state.active_topic)

        state.relevant_documents = documents or []

        formatted_docs = format_documents(
            state.relevant_documents
        )

        recent_messages = "\n".join(
            [
                f"{m['role']}: {m['content']}"
                for m in state.messages[-8:]
            ]
        )

        conversation_input = f"""
            LATEST USER MESSAGE:
            {state.query}

            FOLLOW-UP:
            {state.is_followup}

            ACTIVE TOPIC:
            {state.active_topic}

            ACTIVE ENTITY:
            {state.active_entity}

            RECENT CONVERSATION HISTORY:
            {recent_messages}

            RELEVANT DOCUMENTS:
            {formatted_docs}

            TASK:
            Answer the user's question as Andreu Ortega using the provided documents.
            Maintain conversational continuity if this is a follow-up question.
        """

        result = await Runner.run(
            conversation_agent,
            conversation_input
        )

        state.messages.append({"role": "assistant", "content": result.final_output})
        state.final_response = result.final_output

        if any(
            getattr(item, "type", None) == "tool_call_output_item"
            for item in result.new_items
        ):
            state.unknown_question_logged = True
            state.pushover_sent = True

        return state
        