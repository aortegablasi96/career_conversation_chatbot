# Career Conversation Chatbot

An AI-powered conversational chatbot that represents Andreu Ortega as a professional persona. Visitors can ask questions about his career, experience, education, and skills in any language and receive accurate, grounded answers via Retrieval-Augmented Generation (RAG).

## How it works

```
User message (Next.js frontend)
  → POST /chat  (FastAPI backend)
  → LangGraph state machine
      ├─ Filter node      — validates the topic is about Andreu, classifies intent (info / contact)
      ├─ Invalid node     — returns a polite fallback in the user's language
      ├─ Contact node     — collects user details and sends a Pushover notification
      └─ Conversation node
            → Query Normalizer agent   (translate to English, expand follow-ups)
            → Hybrid retrieval         (Chroma vector + BM25) + Cohere reranking
            → Conversation agent       (answers as Andreu using retrieved documents)
  → Response returned to frontend
```

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 4 |
| API | FastAPI |
| Orchestration | LangGraph |
| Agents | OpenAI Agents SDK (gpt-4o-mini) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector DB | Chroma |
| Retrieval | Hybrid semantic + BM25, reranked by Cohere |
| Notifications | Pushover |
| Bot | Telegram |
| Observability | LangSmith |
| Deployment | Backend → Render · Frontend → Vercel |

## Repository structure

```
career_conversation_chatbot/
├── backend/          # Python backend (FastAPI + LangGraph + agents)
└── frontend/         # Next.js frontend
```

See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md) for details on each service.

## Quick start

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in environment variables
cp .env.example .env

# Start the API server
python -m uvicorn backend.api.api_main:app --host 0.0.0.0 --port 8000 --reload

# (Re)build the vector knowledge base
python backend/data_pipeline/ingest.py
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy and fill in environment variables
# set NEXT_PUBLIC_API_URL=http://localhost:8000

# Start the dev server
npm run dev
```

## Environment variables

### Backend (`.env`)

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | LLM and embeddings |
| `COHERE_API_KEY` | Retrieval reranking |
| `LANGSMITH_API_KEY` | Agent observability |
| `LANGSMITH_TRACING` | Enable LangSmith tracing (`true`/`false`) |
| `PUSHOVER_USER` | Pushover user key |
| `PUSHOVER_TOKEN` | Pushover app token |
| `BOT_TOKEN` | Telegram bot token |
| `SENDGRID_API_KEY` | Email integration |

### Frontend (`frontend/.env.local`)

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL |

## Deployment

- **Backend**: Render (free plan, configured via `render.yaml`). Scales to zero when idle.
- **Frontend**: Vercel.
- **Cold-start mitigation**: The `AppLoader` component calls `POST /warmup` before showing the chat UI, so the Render instance is warm by the time the user types their first message.
