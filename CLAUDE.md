# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered conversational chatbot representing Andreu Ortega as a professional persona. Uses RAG (Retrieval-Augmented Generation) with a LangGraph state machine, specialized OpenAI Agents SDK agents, and a hybrid vector + BM25 knowledge base. Supports multilingual queries (English, Spanish, Italian, Catalan).

## Commands

### Backend (Python 3.11.9, from `backend/` directory)
```bash
# Install dependencies (uv preferred; pip also works)
uv sync                        # preferred — respects uv.lock
pip install -r requirements.txt  # fallback

# Run backend dev server
python -m uvicorn api.api_main:app --host 0.0.0.0 --port 8000 --reload

# Rebuild vector knowledge base from markdown files
python data_pipeline/ingest.py

# Local Gradio UI (backend-only testing, no frontend needed)
python app/career_conversation_chatbot.py
```

### Frontend (Next.js, from `frontend/` directory)
```bash
npm run dev       # Dev server on localhost:3000
npm run build     # Production build
npm run lint      # ESLint (eslint-config-next/core-web-vitals + typescript)
npm start         # Start production build
```

There is no test suite for either backend or frontend.

## Architecture

### Request Flow
```
User message (Next.js)
  → AppLoader: POST /warmup (builds LangGraph engine once, on cold start)
  → POST /chat (FastAPI, per-user session)
  → ChatbotService → LangGraph state machine
      ├─ filter node: validates topic is about Andreu, classifies intent (info/contact)
      ├─ invalid node: returns fixed fallback response
      ├─ contact node: collects user info, sends Pushover notification
      └─ info node:
            → QueryNormalizerAgent (translate, expand follow-ups)
            → Hybrid retrieval (Chroma vector + BM25) + Cohere rerank
            → ConversationAgent (generates response with context)
  → JSON response back to frontend
```

### Backend Structure (`backend/`)
- `api/api_main.py` — FastAPI app, CORS, router registration
- `api/routes/chatbot.py` — `/warmup` and `/chat` endpoints; global shared engine + lightweight per-user sessions
- `api/routes/telegram.py` — Telegram webhook integration
- `api/routes/app.py` — `/health` endpoint
- `app/career_conversation_chatbot.py` — `ChatbotService` class; also launches Gradio UI when run directly
- `graph/graph.py` — `Graph` class: builds LangGraph `StateGraph`, uses `MemorySaver` for checkpointing
- `graph/nodes.py` — `Nodes` class: async methods for each graph node; imports and calls all four agents
- `models/state.py` — Pydantic `State` model passed through the graph
- `agents_folder/` — OpenAI Agents SDK agent definitions (one file per agent)
- `data_pipeline/ingest.py` — loads markdown from `knowledge-base/`, embeds with `text-embedding-3-small`, stores in Chroma (no chunking currently)
- `storage/vector_db/` — persistent Chroma vector database (not committed)

### Frontend Structure (`frontend/`)
- Next.js 15 App Router with TypeScript
- `app/layout.tsx` — wraps everything in `AppLoader` for warmup
- `app/page.tsx` — renders `ChatWindow`
- `components/AppLoader.tsx` — hits `/warmup` on mount, shows spinner until ready; **hardcodes the Render backend URL** (change this when developing against a local backend)
- `components/ChatWindow.tsx` — full chat UI; manages messages, loading state, per-session UUID
- `lib/api.ts` — `sendMessage()` using `NEXT_PUBLIC_API_URL`
- Tailwind CSS 4, Framer Motion, ReactMarkdown + remark-gfm

### State Machine (`backend/models/state.py`)
Pydantic `State` with 16 fields passed through the entire graph:

| Field | Set by |
|---|---|
| `query` | Caller |
| `messages` | Caller (8-message window) |
| `filter_validation` | filter node |
| `subject_is_andreu` | filter node |
| `filter_classification` | filter node (`"info"` / `"contact"`) |
| `detected_language` | filter node |
| `is_followup` | filter node |
| `active_topic` / `active_entity` | filter node |
| `retrieval_query` | info node (after normalisation) |
| `relevant_documents` | info node (after hybrid retrieval) |
| `final_response` | whichever terminal node executes |
| `unknown_question_logged` | conversation node |
| `contact_recorded` / `pushover_sent` | contact node |
| `trace_id` | Caller (doubles as LangGraph `thread_id`) |

### Agents (`backend/agents_folder/`)
All agents use the OpenAI Agents SDK (`from agents import Agent, Runner, function_tool`) with Pydantic structured outputs:

| Agent | Model | Role |
|---|---|---|
| `filter_agent` | `gpt-4.1-nano` | Classifies intent, detects language/follow-up; structured `FilterOutput`; uses in-memory prompt caching |
| `query_normalizer_agent` | `gpt-4.1-nano` | Translates + expands query for retrieval; structured `QueryNormalizedOutput` |
| `contact_agent` | `gpt-4o-mini` | Collects contact info, calls `RecordUserDetailsTool` (Pushover) |
| `conversation_agent` | `gpt-4o-mini` | Answers as Andreu using retrieved docs; calls `RecordQuestionsTool` for unknowns |

### Hybrid Retrieval (in `agents_folder/conversation_agent.py`)
Retrieval logic lives alongside the conversation agent, not in a separate module:
1. Semantic vector search via Chroma (up to 3 query variants × K results); applies `doc_type` metadata filter via `TOPIC_TO_DOC_TYPE` when `active_topic` is set
2. BM25 lexical search on `retrieval_keywords`
3. All queries run concurrently via `asyncio.gather()`
4. Merge + deduplicate by `chunk_id` or `source` metadata
5. Cohere `rerank-english-v3.0` reranking (top 15, `FILTER_K=15`)

### Knowledge Base
Markdown files in `backend/knowledge-base/` organized by: `certifications/`, `courses/`, `experiences/`, `languages/`, `profile/`, `skills/`, `studies/`. The ingest pipeline prepends a `[Category: {doc_type} | Document: {name}]` prefix before embedding, stores whole documents as single vectors (no chunking), and serialises the BM25 index to `storage/bm25_index.pkl`. Both storage artifacts are gitignored.

## Engine / Session Architecture

The backend uses a two-tier pattern to avoid rebuilding LangGraph on every request:
- **Global engine** (`ChatbotService` + `Graph`): built once on `/warmup`, shared across all users
- **Per-user session**: lightweight dict with `trace_id` (UUID) and `memory` (last 8 messages), stored in a `TTLCache(maxsize=500, ttl=3600)` — sessions expire after 1 hour of inactivity

The `trace_id` doubles as the LangGraph `thread_id` for `MemorySaver` checkpointing.

## Environment Variables

**Backend** (`.env` in `backend/`):
- `OPENAI_API_KEY` — LLM and embeddings
- `LANGSMITH_API_KEY`, `LANGSMITH_TRACING` — agent observability
- `COHERE_API_KEY` — retrieval reranking
- `PUSHOVER_USER`, `PUSHOVER_TOKEN` — contact request and unknown question notifications
- `BOT_TOKEN` — Telegram bot
- `TELEGRAM_WEBHOOK_URL` — optional override for Telegram webhook base URL (defaults to Render's `RENDER_EXTERNAL_URL`; set this when testing locally via ngrok)

**Frontend** (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — backend URL (used by `lib/api.ts`; `AppLoader.tsx` hardcodes the Render URL separately)

## Deployment

- **Backend**: Render (configured via `backend/render.yaml`, free plan, auto-scales to zero). Build: `pip install -r requirements.txt`. Start: `python -m uvicorn api.api_main:app --host 0.0.0.0 --port $PORT`
- **Frontend**: Vercel
- **AppLoader pattern**: Frontend hits `/warmup` on page load to pre-warm the backend before showing the chat UI, mitigating Render cold starts
- **CORS origins**: `localhost:3000`, `career-conversation-chatbot.onrender.com`, `career-conversation-chatbot.vercel.app`

## Key Design Decisions

- **Conversation memory**: 8-message sliding window in the per-user session dict; passed as `history` into each `run_superstep` call
- **Multilingual**: QueryNormalizerAgent translates non-English queries to English before retrieval; ConversationAgent responds in the user's detected language
- **Follow-up handling**: FilterAgent sets `is_followup`; QueryNormalizerAgent resolves ambiguous references using `active_topic` / `active_entity` from state
- **No chunking**: ingest currently stores whole markdown documents as single vectors (the `create_chunks` call in `ingest.py` is commented out)
- **Pushover for observability**: both unknown questions and contact requests trigger Pushover push notifications in real time
