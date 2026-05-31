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
│   ├── AppLoader.tsx        # Calls POST /warmup, shows loading state until backend is ready
│   └── ChatWindow.tsx       # Full chat UI: message list, input, send logic
│
├── lib/
│   └── api.ts               # sendMessage(message, threadId) — POST /chat wrapper
│
└── public/                  # Static assets (avatars, icons)
```

## Key design decisions

**AppLoader warmup pattern**  
Because the backend runs on Render's free plan and scales to zero, `AppLoader` calls `POST /warmup` on mount and blocks the chat UI until the backend responds `{ status: "ready" }`. This hides the cold-start latency from the user.

**Thread identity**  
Each browser session generates a UUID (`threadId`) passed as `user_id` in every `/chat` request. The backend uses this to look up the per-user conversation memory.

**Markdown rendering**  
Bot responses are rendered with `react-markdown` so the conversation agent can use headings, bullet points, and bold text.

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
