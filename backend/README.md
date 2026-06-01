# Backend

Python backend for the Career Conversation Chatbot. Built with FastAPI, LangGraph, and the OpenAI Agents SDK.

## Structure

```
backend/
├── api/
│   ├── api_main.py          # FastAPI app: CORS, router registration
│   └── routes/
│       ├── chatbot.py       # /warmup and /chat endpoints; engine + session management
│       ├── telegram.py      # Telegram webhook handler
│       └── app.py           # Health / utility routes
│
├── app/
│   └── career_conversation_chatbot.py  # ChatbotService: thin wrapper around Graph
│
├── graph/
│   ├── graph.py             # LangGraph state machine definition and runner
│   └── nodes.py             # Node implementations (filter, invalid, contact, conversation)
│
├── agents_folder/
│   ├── filter_agent.py          # Validates topic, classifies intent, detects language
│   ├── contact_agent.py         # Collects contact details, triggers Pushover
│   ├── query_normalizer_agent.py # Translates queries to English, expands follow-ups
│   └── conversation_agent.py    # RAG response generator; also owns hybrid retrieval logic
│
├── integrations/
│   └── pushover.py              # Shared async Pushover notification utility
│
├── models/
│   └── state.py             # Pydantic State model shared across the entire graph
│
├── resources/
│   ├── invalid_messages.py  # Localised fallback messages (en, es, it, ca)
│   └── start_messages.py    # Greeting copy
│
├── data_pipeline/
│   ├── ingest.py            # Parses knowledge-base markdown → builds Chroma vector DB
│   └── vector_db_visualizer.py  # Debug tool: inspect stored chunks
│
├── knowledge-base/          # Markdown source files ingested into the vector DB
│   ├── certifications/
│   ├── courses/
│   ├── experiences/
│   ├── languages/
│   ├── profile/
│   ├── skills/
│   └── studies/
│
└── storage/
    ├── vector_db/           # Persisted Chroma database (not committed to git)
    └── bm25_index.pkl       # Serialised BM25 index (not committed to git)
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/warmup` | Pre-initialises the LangGraph engine (called by frontend AppLoader) |
| `POST` | `/chat` | Accepts `{ user_id, message }` (max 2000 chars), returns `{ reply }`. Returns HTTP 503 if engine not ready, HTTP 429 if rate-limit exceeded (20 req/min per user), HTTP 422 if input invalid. |
| `POST` | `/telegram` | Telegram webhook |

## State machine

The graph in `graph/graph.py` uses the Pydantic `State` model and four nodes:

```
START → filter → [invalid | contact | info] → END
```

`filter_router` reads `state.filter_validation` and `state.filter_classification` to choose the branch.

**State fields**

| Field | Set by |
|---|---|
| `query` | Caller |
| `messages` | Caller (8-message window) |
| `filter_validation` | filter node |
| `filter_classification` | filter node (`"info"` / `"contact"`) |
| `detected_language` | filter node |
| `is_followup` | filter node |
| `retrieval_query` | conversation node (after normalisation) |
| `relevant_documents` | conversation node (after hybrid retrieval) |
| `active_topic` / `active_entity` | filter node |
| `final_response` | whichever terminal node executes |
| `contact_recorded`, `pushover_sent`, `unknown_question_logged` | contact / conversation nodes |

## Retrieval pipeline

Implemented in `agents_folder/conversation_agent.py → search_knowledge_base()`:

1. **Semantic retrieval** — Chroma with `text-embedding-3-small` embeddings, queried with the normalised query plus up to 2 expanded variants. When `active_topic` is known, the retriever applies a `doc_type` metadata filter via `TOPIC_TO_DOC_TYPE`.
2. **BM25 retrieval** — keyword-based lexical search; loaded from `storage/bm25_index.pkl` (serialised by ingest pipeline) with fallback rebuild from Chroma.
3. **Concurrent dispatch** — all semantic queries and the BM25 lookup run in parallel via `asyncio.gather()`.
4. **Merge + deduplication** — by `chunk_id` / `source` metadata.
5. **Cohere reranking** — `rerank-english-v3.0`, top 15 results (`FILTER_K=15`), offloaded to a thread-pool executor to avoid blocking the event loop.

## Session and engine model

- **One global engine** (`ChatbotService`) is built once on `/warmup`. Building the graph is expensive (loads tools, loads BM25 index from disk), so it happens only once.
- **Per-user sessions** are lightweight dicts `{ trace_id, memory }` stored in a `TTLCache(maxsize=500, ttl=3600)` — sessions expire after 1 hour of inactivity and the store is bounded to 500 concurrent users.
- Memory holds the last 8 messages per session (reset on expiry or server restart).
- **Telegram** shares the same global engine instead of creating a separate `ChatbotService` per user.

## Knowledge base

Markdown files under `backend/knowledge-base/` are the source of truth. Run the ingest pipeline after adding or editing content:

```bash
python backend/data_pipeline/ingest.py
```

Each markdown file is stored as a single vector (no chunking). A `[Category: {doc_type} | Document: {name}]` prefix is prepended to each document before embedding so the vector captures the document's identity. The pipeline also serialises the fitted BM25 index to `backend/storage/bm25_index.pkl`.

## Running locally

```bash
pip install -r requirements.txt
python -m uvicorn backend.api.api_main:app --host 0.0.0.0 --port 8000 --reload
```

Required environment variables: see root [`README.md`](../README.md#environment-variables).
