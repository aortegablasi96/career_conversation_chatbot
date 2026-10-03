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
| Agents | OpenAI Agents SDK (gpt-4.1-nano / gpt-4o-mini) |
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

### Frontend (`frontend/.env.local`)

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend base URL |

## Deployment

- **Backend**: Render (free plan, configured via `render.yaml`). Scales to zero when idle.
- **Frontend**: Vercel.
- **Cold-start mitigation**: The `AppLoader` component calls `POST /warmup` before showing the chat UI. It retries up to 5 times with exponential backoff (3 s, 6 s, 12 s, 24 s) and renders a visible error state with a Refresh button if all attempts fail. The chat input is disabled until warmup succeeds.

## Callers and allowed origins

The API is called from browsers by two sites, so `backend/api/api_main.py` allows their origins in `CORSMiddleware`:

| Origin | Who calls it |
|---|---|
| `https://career-conversation-chatbot.vercel.app` | This repository's frontend |
| `https://career-conversation-chatbot.onrender.com` | The API's own address |
| `https://andreuortegablasi.com` | The career site ([aortegablasi96/career-site](https://github.com/aortegablasi96/career-site)), whose chat is on every page |
| `https://career-site-*-andreus-projects-f43ec5ad.vercel.app` | The career site's Vercel previews, matched by `allow_origin_regex` |
| `http://localhost:3000` | Local development of either frontend |

`allow_origins` matches exact addresses only; a `*` inside an address there is not a wildcard. The previews' pattern is therefore `allow_origin_regex`, `^https://career-site-[a-z0-9-]+-andreus-projects-f43ec5ad\.vercel\.app$`, which pins the Vercel team's suffix so that no other `vercel.app` site is allowed. It changes if the career site moves to another Vercel team.

The career site calls `POST /warmup` as soon as a page loads, then `POST /chat` with `{ user_id, message }`, where `user_id` is a random UUID per conversation. It sends no credentials. It relies on this contract, recorded in its [ADR-028](https://github.com/aortegablasi96/career-site/blob/main/docs/decisions/architecture-decisions/ADR-028-a-chat-calls-the-digital-twins-api-from-the-readers-browser.md), so a change to it breaks the career site's chat:

- a `reply` string in a 200 answer to `/chat`, written in Markdown;
- 503 with `Retry-After` while the engine is warming up;
- 429 above 20 requests a minute for one `user_id`;
- messages of at most 2,000 characters.
