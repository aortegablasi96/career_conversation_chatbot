from pathlib import Path
from agents import Agent, function_tool, ModelSettings
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document


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

    for doc in chroma_docs + bm_docs:
        cid = doc.metadata.get("chunk_id") or doc.metadata.get("source")
        if cid not in seen:
            seen.add(cid)
            combined.append(doc)

    return combined

INSTRUCTIONS = "You are a look-up agent that given a query will look up in the database, using the tool provided, the relevant content found."

lookup_agent = Agent(
    name="LookupAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=[search_knowledge_base],
    model_settings=ModelSettings(tool_choice="required")
)