from pathlib import Path
from typing import Optional, Any
from agents import Agent, AgentOutputSchema, function_tool, ModelSettings
from dotenv import load_dotenv
from langchain_cohere import CohereRerank
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from pydantic import BaseModel, Field


load_dotenv(override=True)

MODEL = "gpt-4o-mini"
DB_NAME = str(Path(__file__).parent.parent.parent / "vector_db")

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
RETRIEVAL_K = 10

vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever()

all_data = vectorstore.get()
documents = [
        Document(page_content=text, metadata=metadata or {})
        for text, metadata in zip(all_data.get("documents", []), all_data.get("metadatas", []))
        if text
    ]

bm25 = BM25Retriever.from_documents(documents)

@function_tool
def search_knowledge_base(query: str):
    """ Retrieve relevant context documents for a question """

    chroma_docs = retriever.invoke(query, k=RETRIEVAL_K)
    bm_docs = bm25.invoke(query,k=RETRIEVAL_K)

    seen = set()
    combined: list[Document] = []

    # To remove duplicates from the same method
    for doc in chroma_docs + bm_docs:
        cid = doc.metadata.get("chunk_id") or doc.metadata.get("source")
        if cid not in seen:
            seen.add(cid)
            combined.append(doc)

    # Reranking section
    reranker = CohereRerank(
        top_n=RETRIEVAL_K,
        model="rerank-english-v3.0",
    )
    
    reranked_indexes = reranker.rerank(query=query,documents=combined)

    reranked_documents = []
    for index in reranked_indexes:
        reranked_documents.append(combined[index["index"]])

    return reranked_documents

INSTRUCTIONS = """You are a look-up agent on behalf of Andreu Ortega. 
Use the tool to retrieve the relevant content related with the query about Andreu Ortega.

When using the tool, always transform the query into English. But answer to the user in the language of the query.
"""

class SearchOutput  (BaseModel):
    output: Optional[list[Any]] = Field(description="List of documents found")
    found_information: bool = Field(description="If information is found or not")

lookup_agent = Agent(
    name="LookupAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=[search_knowledge_base],
    model_settings=ModelSettings(tool_choice="required"),
    output_type=AgentOutputSchema(SearchOutput,strict_json_schema=False)
)