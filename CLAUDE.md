# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered conversational chatbot representing Andreu Ortega as a professional persona. Uses RAG (Retrieval-Augmented Generation) with a LangGraph state machine, specialized OpenAI agents, and a hybrid vector + BM25 knowledge base. Supports multilingual queries (English, Spanish, Italian, Catalan).

## Commands

### Backend (Python, from repo root)
```bash
# Run backend dev server
python -m uvicorn api.api_main:app --host 0.0.0.0 --port 8000 --reload

# Rebuild vector knowledge base from markdown files
python backend/data_pipeline/ingest.py

# Package manager: uv (uv.lock present) or pip
pip install -r requirements.txt
```

### Frontend (Next.js, from `frontend/` directory)
```bash
npm run dev       # Dev server on localhost:3000
npm run build     # Production build
npm run lint      # ESLint
npm start         # Start production build
```

## Architecture

### Request Flow
```
User message (Next.js) 
  → POST /chat (FastAPI)
  → ChatbotService → LangGraph state machine
      ├─ Filter Node: validates topic is about Andreu, classifies intent (info/contact)
      ├─ Invalid Node: returns fallback response
      ├─ Contact Node: collects user info, sends Pushover notification
      └─ Conversation Node:
            → Query Normalizer Agent (translate, expand follow-ups)
            → Hybrid retrieval (Chroma vector + BM25) + Cohere rerank
            → Conversation Agent (generates response with context)
  → Response streamed back to frontend
```

### Backend Structure (`api/` + `backend/`)
- `api/api_main.py` — FastAPI app, CORS, routes, AppLoader warmup
- `api/chatbot_service.py` — bridges HTTP requests to LangGraph engine
- `backend/graph/` — LangGraph state machine: `graph.py`, `state.py`, nodes in `nodes/`
- `backend/agents/` — OpenAI Agents SDK wrappers: filter, contact, query_normalizer, conversation
- `backend/knowledge_base/` — hybrid retrieval: `vector_store.py`, `bm25_retriever.py`, `retriever.py`, `reranker.py`
- `backend/data_pipeline/ingest.py` — parses markdown from `backend/knowledge-base/` and builds Chroma DB
- `backend/storage/vector_db/` — persistent Chroma vector database (not committed)
- `backend/telegram/` — Telegram bot webhook integration

### Frontend Structure (`frontend/`)
- Next.js 15 App Router with TypeScript
- `src/app/` — pages and layout
- `src/components/` — UI components (chat interface, AppLoader, messages)
- `src/hooks/` — custom React hooks for chat state
- `src/lib/` — API client utilities
- Tailwind CSS 4, Framer Motion for animations

### State Machine (`backend/graph/state.py`)
Pydantic model with ~13 fields tracking: query validation, intent classification, language, conversational context (topic/entity), retrieved documents, final response, and observability flags.

### Knowledge Base
Markdown files in `backend/knowledge-base/` organized by: `certifications/`, `courses/`, `experiences/`, `languages/`, `profile/`, `skills/`, `studies/`. The ingest pipeline chunks these into Chroma with OpenAI `text-embedding-3-small` embeddings.

## Environment Variables

**Backend** (`.env` in repo root):
- `OPENAI_API_KEY` — LLM and embeddings
- `LANGSMITH_API_KEY`, `LANGSMITH_TRACING` — agent observability
- `COHERE_API_KEY` — retrieval reranking
- `PUSHOVER_USER`, `PUSHOVER_TOKEN` — contact request notifications
- `BOT_TOKEN` — Telegram bot
- `SENDGRID_API_KEY` — email

**Frontend** (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — backend URL (defaults to Render deployment)

## Deployment

- **Backend**: Render (configured via `render.yaml`, free plan, auto-scales to zero)
- **Frontend**: Vercel
- **AppLoader pattern**: Frontend pre-warms the backend on load to mitigate cold starts on free Render tier
- **CORS origins**: localhost:3000, Render backend, Vercel frontend domains

## Key Design Decisions

- **Conversation memory**: 8-message sliding window stored in-memory per session (keyed by trace ID)
- **Multilingual**: Query Normalizer Agent translates non-English queries to English before retrieval, responds in the user's language
- **Follow-up handling**: Normalizer also expands ambiguous follow-up queries using conversation context before retrieval
- **Hybrid retrieval**: Combines dense (Chroma + OpenAI embeddings) and sparse (BM25) retrieval, reranked by Cohere
