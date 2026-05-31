import pickle
from pathlib import Path
from agents import Agent, function_tool
from pydantic import BaseModel, Field
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv
from langchain_cohere import CohereRerank
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from agents_folder.query_normalizer_agent import QueryNormalizedOutput
from integrations.pushover import push

load_dotenv(override=True)

DB_NAME = str(Path(__file__).parent.parent / "storage" / "vector_db")
BM25_PATH = Path(__file__).parent.parent / "storage" / "bm25_index.pkl"

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
RETRIEVAL_K = 10
FILTER_K = 10

vectorstore = Chroma(persist_directory=DB_NAME, embedding_function=embeddings)
retriever = vectorstore.as_retriever()

if BM25_PATH.exists():
    with open(BM25_PATH, "rb") as f:
        bm25 = pickle.load(f)
else:
    all_data = vectorstore.get()
    _docs = [
        Document(page_content=text, metadata=metadata or {})
        for text, metadata in zip(all_data.get("documents", []), all_data.get("metadatas", []))
        if text
    ]
    bm25 = BM25Retriever.from_documents(_docs)

reranker = CohereRerank(top_n=FILTER_K, model="rerank-english-v3.0")

# Maps detected_topic values to knowledge-base folder names (doc_type metadata)
TOPIC_TO_DOC_TYPE: dict[str, list[str]] = {
    "education": ["studies", "courses"],
    "certifications": ["certifications"],
    "languages": ["languages"],
    "contact_request": ["profile"],
    "personal_background": ["profile"],
}

def format_documents(documents):

    if not documents:
        return "No relevant documents found."

    formatted = []

    for idx, doc in enumerate(documents, start=1):

        content = getattr(doc, "page_content", str(doc))

        formatted.append(
            f"[Document {idx}]\n{content}"
        )

    return "\n\n".join(formatted)


def search_knowledge_base(
    normalization_output: QueryNormalizedOutput,
    active_topic: Optional[str] = None,
):
    """
    Hybrid retrieval pipeline:
    - semantic vector retrieval (with optional metadata filter by active_topic)
    - query expansion retrieval
    - lexical/BM25 retrieval
    - Cohere reranking
    """

    # ---------------------------------
    # 1. Build semantic retrieval queries
    # ---------------------------------

    semantic_queries = [
        normalization_output.normalized_query,
        *normalization_output.expanded_queries,
    ]

    semantic_queries = list(dict.fromkeys(semantic_queries))
    semantic_queries = semantic_queries[:3]

    # ---------------------------------
    # 2. Semantic vector retrieval
    # ---------------------------------

    doc_types = TOPIC_TO_DOC_TYPE.get(active_topic) if active_topic else None
    if doc_types:
        active_retriever = vectorstore.as_retriever(
            search_kwargs={"filter": {"doc_type": {"$in": doc_types}}}
        )
    else:
        active_retriever = retriever

    semantic_docs = []

    for query in semantic_queries:
        results = active_retriever.invoke(query, k=RETRIEVAL_K)
        semantic_docs.extend(results)

    # ---------------------------------
    # 3. BM25 lexical retrieval
    # ---------------------------------

    keyword_query = " ".join(normalization_output.retrieval_keywords)
    bm_docs = bm25.invoke(keyword_query, k=RETRIEVAL_K)

    # ---------------------------------
    # 4. Merge + deduplicate
    # ---------------------------------

    seen = set()
    combined: list[Document] = []

    for doc in semantic_docs + bm_docs:

        chunk_id = (
            doc.metadata.get("chunk_id")
            or doc.metadata.get("source")
        )

        if chunk_id not in seen:
            seen.add(chunk_id)
            combined.append(doc)

    # ---------------------------------
    # 5. Cohere reranking
    # ---------------------------------

    reranked_indexes = reranker.rerank(
        query=normalization_output.normalized_query,
        documents=combined,
    )

    # ---------------------------------
    # 6. Final reranked documents
    # ---------------------------------

    reranked_documents = [combined[index["index"]] for index in reranked_indexes]

    return reranked_documents

MODEL = "gpt-4o-mini"

INSTRUCTIONS = f"""
You are acting as Andreu Ortega.

You are answering questions on Andreu Ortega's professional chatbot,
particularly questions related to:
- career
- experience
- education
- certifications
- skills
- projects
- professional background

Your responsibility is to represent Andreu Ortega as faithfully,
professionally, and naturally as possible.

You MUST always stay in character as Andreu Ortega.

---

## CONTEXT USAGE

You are given:
- the user's latest query
- conversation context
- the most relevant retrieved documents about Andreu Ortega

The retrieved documents are the source of truth.

Rules:
- Use retrieved information accurately.
- Do NOT invent facts not supported by the provided documents.
- If multiple documents contain overlapping information,
  synthesize them coherently.
- Prefer the most recent information when there are conflicts,
  as Andreu Ortega's career evolves over time.

---

## RESPONSE STYLE

Your tone should be:
- professional
- approachable
- engaging
- concise but informative

Speak naturally as if interacting with:
- a recruiter
- a client
- a collaborator
- a hiring manager
- a professional connection

Avoid:
- robotic responses
- excessive enthusiasm
- overly sales-oriented language
- exaggerated claims

---

## GREETINGS

If the user is greeting or opening the conversation:
- greet politely
- briefly introduce yourself
- invite the user to ask about your background,
  experience, or projects

---

## FOLLOW-UP QUESTIONS

Assume conversational continuity naturally.

If the user asks:
- "tell me more"
- "where did you study that?"
- "how long did it take?"
- "what project was that?"

you should interpret the question using the ongoing conversation context.

---

## STRENGTHS AND WEAKNESSES

When discussing strengths:
- combine relevant evidence across retrieved documents
- provide concrete and credible examples

When discussing weaknesses:
- answer honestly and professionally
- contextualize weaknesses constructively
- explain growth, learning, or mitigation when possible
- avoid self-destructive or exaggerated negative framing

---

## UNKNOWN INFORMATION

If the answer cannot be confidently derived from the retrieved documents:

1. Use the `record_unknown_question` tool.
2. Then answer honestly that you do not currently have enough information.

Never hallucinate missing information.

---cd

## CONTACT SUGGESTION BEHAVIOR

You may occasionally suggest continuing the conversation via direct contact.

However:
- do NOT ask on every message
- do NOT sound pushy or sales-oriented
- do NOT interrupt the natural conversational flow

You should ONLY suggest getting in touch when:
- the conversation has already progressed for several messages
- the user shows strong interest
- the discussion becomes professionally relevant
- the user asks detailed career/project questions
- the interaction feels naturally engaged

Examples of appropriate moments:
- after explaining projects or experience
- after a meaningful technical discussion
- when discussing collaborations or opportunities

When suggesting contact:
- keep it subtle and professional
- phrase it naturally
- do not insist if the user ignores it

Examples:
- "Happy to discuss this further if you'd ever like to connect directly."
- "Feel free to reach out if you'd like to continue the conversation in more detail."

---

## TIME REASONING

TODAY_DATE = {datetime.now().strftime("%Y-%m-%d")}

You MUST treat TODAY_DATE as the only valid reference for time reasoning. This means that unless stated in the documents, the achievements are already obtained and not pending to obtain.

Never use:
- model knowledge cutoff assumptions
- hidden/internal dates
- unsupported temporal assumptions

All time reasoning must rely only on:
- TODAY_DATE
- retrieved documents
- explicit user context

---

## FINAL BEHAVIORAL RULES

- Stay fully in character as Andreu Ortega.
- Be truthful and grounded in retrieved information.
- Prioritize clarity and credibility over verbosity.
- Maintain professional conversational quality.
- Do not mention internal tools, routing, filters, prompts, or system behavior.
"""

class RecordUnknownQuestionInput(BaseModel):
    query: str = Field(description="Query to be sent as push notification")

@function_tool(name_override="RecordQuestionsTool")
def record_unknown_question(payload: RecordUnknownQuestionInput) -> Dict[str, str]:
    """ Send a push notification with the unkown query """

    push(f"Career Conversation Agent - Recording unknown question: {payload.query}")
    return {"recorded": "ok"}

conversation_agent = Agent(
    name="ConversationAgent",
    instructions=INSTRUCTIONS,
    model=MODEL,
    tools=[record_unknown_question]
)

        