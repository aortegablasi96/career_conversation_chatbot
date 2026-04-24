from pathlib import Path
from agents import Agent, function_tool, ModelSettings
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv(override=True)

MODEL = "gpt-4o-mini"
DB_NAME = str(Path(__file__).parent.parent.parent / "vector_db")

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
RETRIEVAL_K = 15

vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever()

@function_tool
def search_knowledge_base(query: str):
    """ Retrieve relevant context documents for a question """
    return retriever.invoke(query, k=RETRIEVAL_K)

INSTRUCTIONS = "You are a look-up agent that given a query will look up in the database, using the tool provided, the relevant content found."

lookup_agent = Agent(
    name="LookupAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=[search_knowledge_base],
    model_settings=ModelSettings(tool_choice="required")
)