from typing import Literal, Optional
from langchain_core.documents import Document
from pydantic import BaseModel, Field 

class State(BaseModel):
    """ To be defined """

    query: str = Field(description="User's query")
    messages: list[str] = Field(description="History of messages")
    filter_validation: bool = Field(description="Output of the filter step")
    filter_classification: Optional[Literal["info","contact"]] = Field(description="Filter classification output")
    found_information: bool = Field(desciption="Database contains information about the query")
    relevant_documents: list[Document] = Field(description="List of documents")
    thread_id: str = Field(description="Run ID")