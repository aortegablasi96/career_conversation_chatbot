from typing import Literal, Optional, Any
from pydantic import BaseModel, Field 

class State(BaseModel):
    """Career Conversation Chatbot LangChain state"""

    # ---- USER INPUT ----
    
    query: str = Field(description="Latest user query")

    messages: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Conversation history"
    )

    # ---- FILTER OUTPUT ----

    filter_validation: bool = Field(
        default=False,
        description="Whether the query is valid"
    )

    subject_is_andreu: bool = Field(
        default=False,
        description="Whether the conversational subject is Andreu Ortega"
    )

    filter_classification: Optional[Literal["info", "contact"]] = Field(
        default=None,
        description="Filter classification output"
    )

    detected_language: Optional[str] = Field(
        default=None,
        description="Language of latest user message"
    )

    is_followup: bool = Field(
        default=False,
        description="Whether query depends on previous context"
    )

    # ---- RETRIEVAL ----

    retrieval_query: Optional[str] = Field(
        default=None,
        description="English-normalized retrieval query"
    )

    relevant_documents: list[Any] = Field(
        default_factory=list,
        description="Retrieved documents"
    )

    # ---- CONVERSATIONAL STATE ----

    active_topic: Optional[str] = Field(
        default=None,
        description="Current discussion topic"
    )

    active_entity: Optional[str] = Field(
        default=None,
        description="Current entity being discussed"
    )

    # ---- OUTPUT ----

    final_response: Optional[str] = Field(
        default=None,
        description="Final generated response"
    )

    # ---- OBSERVABILITY ----

    unknown_question_logged: bool = Field(
        default=False,
        description="Whether an unknown question was recorded"
    )

    contact_recorded: bool = Field(
        default=False,
        description="Whether contact details were recorded"
    )

    pushover_sent: bool = Field(
        default=False,
        description="Whether a pushover notification was sent"
    )

    trace_id: str = Field(
        description="Trace ID"
    )