# Frontend

Next.js 15 frontend for the Career Conversation Chatbot.

## Structure

```
frontend/
├── app/
│   ├── layout.tsx           # Root layout
│   ├── page.tsx             # Single page — renders <ChatWindow />
│   ├── globals.css          # Global styles (Tailwind base)
│   └── api/
│       └── health/
│           └── route.ts     # Internal health-check route
│
├── components/
│   ├── AppLoader.tsx        # Calls POST /warmup with retry/backoff; shows error state on failure
│   ├── ChatWindow.tsx       # Full chat UI: message list, input, send logic, char counter
│   └── ChatErrorBoundary.tsx  # Error boundary: recoverable fallback UI for runtime errors
│
├── context/
│   └── AppReadyContext.tsx  # Context exposing backend-ready flag; read by ChatWindow
│
├── lib/
│   └── api.ts               # sendMessage() — POST /chat; exports WarmingUpError, RateLimitError
│
└── public/                  # Static assets (avatars, icons)
```

## Key design decisions

**AppLoader warmup pattern**  
Because the backend runs on Render's free plan and scales to zero, `AppLoader` calls `POST /warmup` (using `NEXT_PUBLIC_API_URL`) on mount and blocks the chat UI until the backend responds. It retries up to 5 times with exponential backoff (3 s, 6 s, 12 s, 24 s). If all attempts fail it renders a "Unable to connect" error state with a Refresh button. The ready flag is shared via `AppReadyContext`; `ChatWindow` disables its input and send button while `appReady` is false.

**Thread identity**  
Each browser session generates a UUID (`threadId`) that is persisted in `sessionStorage`. On mount, `ChatWindow` reads back the stored ID so conversation history survives page refreshes within the same session.

**Error handling**  
`api.ts` throws `WarmingUpError` on HTTP 503 and `RateLimitError` on HTTP 429. `ChatWindow` catches each and renders a specific inline assistant message ("still starting up" or "sending too quickly") instead of a blank or broken message.

**Character limit**  
The input is capped at 2000 characters (matching the server-side `max_length` validation). A subtle counter appears at 1800 chars (amber) and turns red above 2000; the send button is disabled when the limit is exceeded.

**Markdown rendering**  
Bot responses are rendered with `react-markdown` + `remark-gfm` so the conversation agent can use headings, bullet points, tables, and bold text.

**Error boundary**  
`ChatErrorBoundary` wraps `<ChatWindow />` in `page.tsx`. A runtime error (e.g. malformed markdown) shows a recoverable "Something went wrong" UI with a "Try again" button instead of a blank screen.

## Running locally

```bash
npm install
npm run dev        # http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` in `.env.local` to point at your local or remote backend:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Other commands

```bash
npm run build   # Production build
npm start       # Serve production build
npm run lint    # ESLint
```

## Deployment

Deployed on Vercel. The `NEXT_PUBLIC_API_URL` environment variable must be set in the Vercel project settings to the Render backend URL.
