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

### Endpoints

| Endpoint | What it does |
| -------- | ------------ |
| `POST /warmup` | Builds the engine once and answers `{"status": "ready"}` |
| `POST /chat` | Takes `{ user_id, message }` and answers `{ user_id, reply }` once the whole turn is done |
| `POST /chat/stream` | Takes the same body and streams the reply as Server-Sent Events. This repository's frontend and the career site use it |

Both chat endpoints run the same checks first: 422 for a message over 2,000 characters, 503 with
`Retry-After: 10` while the engine is warming up, and 429 above 20 requests a minute for one
`user_id`. These come back as JSON before anything is streamed. The Telegram bot calls the engine
through its own webhook, not through these endpoints.

Otherwise `/chat/stream` answers 200 with `text/event-stream`, and sends one `data:` line of JSON
per frame, each followed by a blank line:

- `{"type": "token", "content": "…"}` for each piece the conversation agent writes;
- `{"type": "done", "content": "…"}` once, at the end, with the whole reply in Markdown;
- `{"type": "error"}` instead of `done`, if the turn fails partway.

A reply the conversation agent doesn't write sends `done` alone, such as the fixed reply to an
off-topic question, or the contact flow's. The session's memory takes the turn only as `done` is
sent. A turn that ends in `error` leaves the memory as it was, and so does one whose caller
disconnects first, since the server then cancels the run.

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

The career site calls `POST /warmup` as soon as a page loads, then `POST /chat/stream` with `{ user_id, message }`, where `user_id` is a random UUID per conversation. It sends no credentials. It relies on this contract, recorded in its [ADR-028](https://github.com/aortegablasi96/career-site/blob/main/docs/decisions/architecture-decisions/ADR-028-a-chat-calls-the-digital-twins-api-from-the-readers-browser.md) and [ADR-030](https://github.com/aortegablasi96/career-site/blob/main/docs/decisions/architecture-decisions/ADR-030-the-chat-reads-the-answer-as-it-is-written.md), so a change to it breaks the career site's chat:

- the frames of `/chat/stream` above, with the whole reply, in Markdown, in `done`;
- the memory taking a turn only as `done` is sent, so the career site can offer to send a question again after `error`;
- the stream reaching the browser piece by piece, unbuffered and uncompressed;
- 503 with `Retry-After` while the engine is warming up;
- 429 above 20 requests a minute for one `user_id`;
- messages of at most 2,000 characters.
