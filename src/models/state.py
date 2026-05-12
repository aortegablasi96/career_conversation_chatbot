from typing import Literal, Optional, Any
from pydantic import BaseModel, Field 

class State(BaseModel):
    """ State model for Career Conversation Chatbot Langchain state """

    query: str = Field(description="User's query")
    messages: list[dict[str, Any]] = Field(description="History of messages")
    filter_validation: bool = Field(description="Output of the filter step")
    filter_classification: Optional[Literal["info","contact"]] = Field(description="Filter classification output")
    found_information: bool = Field(desciption="Database contains information about the query")
    relevant_documents: list[Any] = Field(description="List of documents")
    trace_id: str = Field(description="Trace ID")