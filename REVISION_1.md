# REVISION.md

---

## Major Problems & Risks

### 1. `active_topic` and `active_entity` are never updated — conversational memory is broken

`filter_agent.py` returns `detected_topic` and `detected_entity` in its `FilterOutput`, but `filter_node` in `nodes.py` never reads those fields and never writes them to `state.active_topic` / `state.active_entity`. Both state fields are `None` on every single turn. The conversation node passes them to the normalizer and to the conversation agent, but they are always empty — meaning follow-up resolution is degraded and "tell me more about the CPMAI one" will never have entity context.

**Fix:** Add to `filter_node`:
```python
state.active_topic = output.detected_topic
state.active_entity = output.detected_entity
```

---

### 2. Document chunking is disabled — retrieval quality is degraded

In `ingest.py` line 65, `create_chunks()` is commented out:
```python
# chunks = create_chunks(documents) for now I do not want chunks
vectorstore = create_embeddings(documents)
```
Entire markdown documents are stored as single embeddings. Long documents exceed the optimal embedding context window, producing noisy, low-precision vectors. The BM25 retriever is also built from whole documents, reducing lexical precision.

---

### 3. Warmup URL is hardcoded in `AppLoader.tsx`

`AppLoader.tsx` line 14 hardcodes `https://career-conversation-chatbot.onrender.com/warmup` instead of using `process.env.NEXT_PUBLIC_API_URL`. Any staging environment, local dev, or URL change is silently ignored — `AppLoader` always hits production.

---

### 4. No warmup retry — UI spins forever on failure

The `catch` block in `AppLoader.tsx` is empty (`// optional retry logic`). If the warmup request fails (Render timeout, network error, 500), `ready` is never set to `true`, the loading spinner never disappears, and the user is permanently locked out with no message.

---

### 5. `warming_up` response is not handled on the frontend

`POST /chat` returns `{ "status": "warming_up" }` when the engine is not ready. `sendMessage` in `lib/api.ts` checks only `response.ok` (HTTP 200), so it passes this through. `ChatWindow` then reads `response.reply`, which is `undefined`, and renders a broken assistant message.

---

### 6. Telegram creates a full `ChatbotService` per user — inconsistent with HTTP route

`telegram.py → get_or_create_session()` calls `ChatbotService(trace_id)` and `await sessions[user_id].setup()` for every new Telegram user. This rebuilds the LangGraph graph and reloads all tools for each user, unlike the HTTP route which shares a single global engine. With multiple Telegram users this causes redundant memory usage and slow first-message latency per user.

---

### 7. `processed_updates` set grows unbounded in Telegram route

`processed_updates = set()` in `telegram.py` accumulates every Telegram `update_id` and is never cleaned up. On a long-running instance this is a slow memory leak.

---

### 8. In-memory session stores lose all conversations on restart

Both `chatbot.py` (`sessions` dict) and `telegram.py` (`sessions`, `chat_histories`) are plain in-memory dicts with no eviction and no persistence. On Render's free plan, the server restarts frequently. Every restart wipes all active sessions and conversation history.

---

### 9. `push()` utility is duplicated across two agents

`contact_agent.py` and `conversation_agent.py` each define an identical `push()` function that calls the Pushover API. Any change to the notification logic (auth, message format, endpoint) must be made twice.

---

### 10. `framer-motion` and `remark-gfm` are not listed in `package.json`

`ChatWindow.tsx` imports from `"framer-motion"` and `"remark-gfm"`, but neither appears in `frontend/package.json` dependencies or devDependencies. They currently work as transitive dependencies of another package, but a clean `npm install` on a different environment may not include them, causing a build failure.

---

### 11. Duplicate import in `filter_agent.py`

`from typing import Literal, Optional` is imported twice — at line 1 and again at line 133 (inside the same file, after the agent instructions string).

---

### 12. No input length validation or rate limiting

`POST /chat` accepts any message string with no length cap and no rate limiting. A malicious user can submit very long inputs or flood the endpoint, consuming OpenAI API credits with no protection.

---

---

## Backend Improvements

### Retrieval & Knowledge Base

- **Re-enable chunking in ingest:** Uncomment `chunks = create_chunks(documents)` and pass chunks (not full documents) to `create_embeddings()`. Current chunk config (2000 tokens / 400 overlap) is already defined — it just isn't used.
  > ✅ **Fixed:** Replaced the unused `RecursiveCharacterTextSplitter(2000/400)` with a two-stage strategy: `MarkdownHeaderTextSplitter` (splits on `#`/`##`/`###` boundaries to preserve document structure) followed by `RecursiveCharacterTextSplitter(500/100)` as a character fallback for long sections. `doc_type` and `source` metadata are propagated to all chunks. Each chunk gets a unique `chunk_id` (`source::index`) so deduplication in `search_knowledge_base` works correctly across chunks from the same file. Result: 118 chunks from 30 documents (was 30 flat documents).

- **Persist the BM25 index:** The BM25 retriever is rebuilt from Chroma every cold start. Serialize it to disk during `ingest.py` and load it at startup to avoid redundant computation.
  > ✅ **Fixed:** Added `save_bm25(chunks)` in `ingest.py` that serialises the fitted `BM25Retriever` to `backend/storage/bm25_index.pkl` via `pickle`. In `conversation_agent.py`, the startup block now loads from that file if it exists and falls back to building from Chroma only when the file is absent (e.g. first run before ingest).

- **Inject source context into every chunk:** After splitting, the document name and category are invisible to BM25 and vector search — they exist only as metadata, which the embedding model never sees. A chunk from `catalan.md` saying "Mother tongue" is semantically identical to the same chunk from `spanish.md`, causing the retriever to return wrong or ambiguous results. Prepend `[Category: {doc_type} | Document: {clean_basename}]` to each chunk's `page_content` before embedding so that every chunk is self-identifying regardless of split position.
  > ✅ **Fixed:** Added a post-split enrichment loop at the end of `create_chunks()` in `ingest.py`. For every final chunk, a `[Category: {doc_type} | Document: {clean_name}]` header is prepended to `page_content`, where `clean_name` is derived from the source file stem (underscores and hyphens replaced with spaces). A `basename_cache` avoids redundant `Path` calls. The `chunk_id` assignment was merged into the same loop.

- **Skip header splitting for very short documents:** Documents under 300 characters produce only micro-chunks (5–15 words each) after `MarkdownHeaderTextSplitter` — too short to carry meaning and harmful to retrieval precision. Short documents are now kept as a single chunk and still receive the source context prefix.
  > ✅ **Fixed:** Added `MIN_CHUNK_CHARS = 300` constant in `ingest.py`. In `create_chunks()`, documents whose stripped content is shorter than this threshold bypass both the header and character splitters and are appended directly to `all_chunks`. The context injection and `chunk_id` assignment still apply in the unified post-split loop.

- **Add `languages` to `TOPIC_TO_DOC_TYPE` metadata filter:** Language-related queries were not scoped to the `languages/` doc_type, causing the retriever to search the entire corpus. Tiny language chunks competed against much larger experience and skill chunks and were frequently outscored, leaving the conversation agent without grounding documents and causing hallucinations (e.g. asserting French instead of Catalan).
  > ✅ **Fixed:** Added `"languages": ["languages"]` to `TOPIC_TO_DOC_TYPE` in `conversation_agent.py`. Language queries now filter Chroma to only the `languages/` folder.

- **Normalize knowledge-base document structure:** All form-like documents (certifications, courses, experiences, studies, languages) used `##`/`###` markdown headers for each individual field (Name, Level, Institution, Duration, etc.). `MarkdownHeaderTextSplitter` split these into micro-chunks — one per field — causing the document's identifying name to be separated from its content in the embedding space. Restructured all 23 affected documents to use a single `#` top-level header containing the entity name, with `**Bold:**` inline labels for each field. Documents now produce one coherent chunk per logical entity rather than several disconnected field-fragments.
  > ✅ **Fixed:** Restructured 23 knowledge-base files across `languages/`, `certifications/`, `courses/`, `experiences/`, and `studies/` folders. No content was changed — only the markdown header hierarchy was flattened. The 7 remaining documents (`profile/`, `skills/`, `experiences/AI-projects.md`) already had adequate structure and were left unchanged.

- **Add metadata filtering to vector retrieval:** Chroma supports filtering by `doc_type` metadata (certifications, experiences, skills, etc.). When `state.active_topic` is known, pass a filter to narrow retrieval instead of searching the full corpus.
  > ✅ **Fixed:** Added `TOPIC_TO_DOC_TYPE` mapping in `conversation_agent.py` (e.g. `"certifications" → ["certifications"]`, `"education" → ["studies", "courses"]`). `search_knowledge_base()` now accepts an optional `active_topic` parameter; when it maps to known doc_types, the Chroma retriever is constructed with a `{"doc_type": {"$in": doc_types}}` filter. `nodes.py` passes `state.active_topic` to the call. Broad topics (`skills`, `career`, `projects`) are deliberately left unfiltered to avoid missing cross-folder results.

### State Machine & Agents

- **Write `active_topic` / `active_entity` from filter output:** (see problem #1) — these fields already exist in `FilterOutput`; they just need to be assigned in `filter_node`.
  > ✅ **Fixed:** Added `state.active_topic = output.detected_topic` and `state.active_entity = output.detected_entity` in `filter_node` in `nodes.py`. These fields are now populated on every turn from the `FilterOutput` structured response.

- **Set observability flags from node code:** `state.contact_recorded`, `state.pushover_sent`, and `state.unknown_question_logged` are defined in `State` but never set to `True`. The nodes should set them after the respective tool call completes, so they can be used for analytics or debugging.
  > ✅ **Fixed:** `contact_node` now sets `state.contact_recorded = True` and `state.pushover_sent = True` after the agent run. `conversation_node` inspects `result.new_items` for any `"tool_call_output_item"` (the only tool in that agent is `RecordQuestionsTool`) and sets `state.unknown_question_logged = True` and `state.pushover_sent = True` accordingly.

- **Extract shared `push()` to a utility module:** Move the Pushover call to `backend/integrations/pushover.py` and import it in both agents.
  > ✅ **Fixed:** Created `backend/integrations/pushover.py` with a single `push(text)` function using `requests`. Both `contact_agent.py` and `conversation_agent.py` now import from `integrations.pushover`; their local `push()` definitions and `import os / import requests` lines are removed.

### API & Session Management

- **Share the global engine with the Telegram route:** Pass the global `engine` from `chatbot.py` into the Telegram handler instead of instantiating a new `ChatbotService` per Telegram user.
  > ✅ **Fixed:** Removed the per-user `ChatbotService` instantiation from `telegram.py`. The module now imports `api.routes.chatbot` as `chatbot_route` and accesses `chatbot_route.engine` / `chatbot_route.engine_ready` at call time (module-level import would capture `None`). Per-user conversation history is still managed by `chat_histories`.

- **Add TTL-based session eviction:** Replace plain `dict` session stores with a bounded LRU/TTL cache (e.g. `cachetools.TTLCache`) to prevent unbounded memory growth and automatically expire stale sessions.
  > ✅ **Fixed:** Replaced `sessions = {}` in `chatbot.py` with `cachetools.TTLCache(maxsize=500, ttl=3600)`. Sessions expire automatically after 1 hour of inactivity; the store is bounded to 500 concurrent users. `cachetools` was already in `requirements.txt`.

- **Cap the `processed_updates` set:** Replace the unbounded set with a `collections.deque(maxlen=N)` or a TTL cache to prevent the slow memory leak in the Telegram route.
  > ✅ **Fixed:** Replaced `processed_updates = set()` with `collections.deque(maxlen=1000)`. `processed_updates.add(update_id)` → `processed_updates.append(update_id)`. The `in` operator works on deques so the duplicate-check logic is unchanged.

- **Return HTTP 503 instead of JSON 200 when not ready:** The `/chat` endpoint returns HTTP 200 with `{ "status": "warming_up" }` when the engine isn't ready. Return a proper `503 Service Unavailable` with a `Retry-After` header so clients can detect and handle it.
  > ✅ **Fixed:** `/chat` now returns `JSONResponse(status_code=503, content={"status": "warming_up"}, headers={"Retry-After": "10"})` when the engine is not ready, instead of HTTP 200.

- **Add input length validation:** Enforce a maximum message length (e.g. 2000 characters) in the `ChatRequest` Pydantic model using `Field(max_length=2000)`.
  > ✅ **Fixed:** `ChatRequest.message` is now declared as `Field(max_length=2000)`. Pydantic rejects messages longer than 2000 characters with a 422 validation error before the handler is reached.

- **Add rate limiting:** Use `slowapi` or a FastAPI middleware to cap requests per IP/user on `/chat`.
  > ✅ **Fixed:** Implemented a simple per-user rate limiter using `cachetools.TTLCache` (no new dependency needed). Keys are `"{user_id}:{minute_bucket}"`, capped at 20 requests per minute per user. Exceeding the limit returns HTTP 429.

- **Fix Telegram history update:** In `telegram.py`, the user message is appended to `history` **after** `bot.chat()` is called, meaning the bot never sees the current user message in the history it receives. The history passed to `chat()` should include the current message, or history should be updated before calling `chat()`.
  > ✅ **Fixed:** The user message is now prepended to `history` **before** calling `chatbot_route.engine.chat(text, history)`, so the bot receives the complete history including the current turn.

### Code Quality

- **Remove duplicate `from typing import Literal, Optional` import** in `filter_agent.py`.
  > ✅ **Fixed:** Removed the second `from typing import Literal, Optional` and `from pydantic import BaseModel, Field` block that appeared after the `INSTRUCTIONS` string in `filter_agent.py` (lines 134–135 originally).

- **Remove unused `HuggingFaceEmbeddings` import** in `ingest.py` (line 6, commented-out code still imports it via the active import line).
  > ✅ **Fixed:** Removed `from langchain_huggingface import HuggingFaceEmbeddings` from `ingest.py`. The commented-out `embeddings = HuggingFaceEmbeddings(...)` line was also removed.

- **Remove the `gradio` import** from `career_conversation_chatbot.py` — Gradio is imported at the top level even though it is only used in the `if __name__ == "__main__"` block. This forces Gradio to be installed as a production dependency when it is only needed for local testing.
  > ✅ **Fixed:** `import gradio as gr` moved inside `async def main()` in `career_conversation_chatbot.py` so Gradio is only imported when the file is run directly (`__main__`), not when `ChatbotService` is imported by the API.

---

## Frontend Improvements

### Correctness & Reliability

- **Use `NEXT_PUBLIC_API_URL` in `AppLoader`:** Replace the hardcoded Render URL with `` `${process.env.NEXT_PUBLIC_API_URL}/warmup` `` so the component respects the configured environment.
  > ✅ **Fixed:** Replaced the hardcoded `https://career-conversation-chatbot.onrender.com/warmup` with `` `${process.env.NEXT_PUBLIC_API_URL}/warmup` `` in `AppLoader.tsx`.

- **Implement warmup retry logic:** Replace the empty `catch` block with 3–5 retries using exponential backoff, and render a visible error state if all attempts fail so the user is not stuck on an infinite spinner.
  > ✅ **Fixed:** Added `attemptWarmup()` helper called in a loop with up to 4 retries (5 total attempts) and exponential backoff (3 s, 6 s, 12 s, 24 s). After all retries are exhausted, `AppLoader` sets an `error` state and renders a "Unable to connect" message with a Refresh button instead of spinning forever.

- **Handle `warming_up` API response:** In `lib/api.ts` or `ChatWindow.tsx`, check if `response.reply` is falsy / `response.status === "warming_up"` and show a "still warming up, please retry" message instead of rendering `undefined`.
  > ✅ **Fixed:** `lib/api.ts` now exports `WarmingUpError` (thrown on 503) and `RateLimitError` (thrown on 429). `ChatWindow.handleSend` catches each error class and renders a specific inline assistant message: "The assistant is still starting up…" for 503 and "You're sending messages too quickly…" for 429.

- **Disable input until warmup is confirmed:** Pass the `ready` flag down from `AppLoader` (or lift it to context) and disable the `ChatWindow` input while the backend is not yet ready.
  > ✅ **Fixed:** Created `frontend/context/AppReadyContext.tsx` with `AppReadyContext` and a `useAppReady()` hook. `AppLoader` now wraps its children in `<AppReadyContext.Provider value={ready}>`. `ChatWindow` reads `appReady` via `useAppReady()` and passes it to `disabled` on both the `<input>` and the send `<button>`, and also guards `handleSend`. The placeholder text changes to "Warming up…" while not ready.

- **Add `framer-motion` and `remark-gfm` to `package.json`:** Declare them as explicit dependencies to guarantee they are available on clean installs.
  > ✅ **Fixed:** Added `"framer-motion": "^11.18.2"` and `"remark-gfm": "^4.0.1"` to `dependencies` in `frontend/package.json`.

### Session & State

- **Persist `threadId` across page refreshes:** `uuidv4()` is called on every mount, so every refresh creates a new session and loses conversation history. Store the generated ID in `sessionStorage` and read it back on mount.
  > ✅ **Fixed:** `threadIdRef` is still initialised with a fresh `uuidv4()` as a safe default. A `useEffect` on mount reads `sessionStorage.getItem("chat_thread_id")` — if found, it overwrites `threadIdRef.current`; if not, it stores the new UUID. The whole block is wrapped in `try/catch` to handle browsers where `sessionStorage` is blocked.

- **Use a stable React key for messages:** Replace `key={index}` with a unique message ID (e.g. a UUID generated when the message is added to state) to avoid DOM reconciliation issues if messages are ever removed or reordered.
  > ✅ **Fixed:** Added an `id: string` field to the `Message` interface. Every message (user, assistant, and error) is created with `id: uuidv4()`. `AnimatePresence` and `motion.div` now use `key={message.id}`.

### UX Polish

- **Add avatar `onError` fallback:** If `/imatge_linkedin.jpg` or the user avatar fails to load, the broken image icon appears inside the rounded container. Provide a fallback to initials or a placeholder icon via `onError`.
  > ✅ **Fixed:** Extracted `AndreuAvatar` and `UserAvatar` components, each with local `imgFailed` state. On `onError`, the `<img>` is replaced by "AO" initials (Andreu) or a `<User>` Lucide icon (user). The container's gradient background shows through in both cases.

- **Add an error boundary around `ChatWindow`:** Wrap the component in a React error boundary so a runtime error (e.g. malformed markdown crashing `ReactMarkdown`) shows a recoverable error UI instead of a blank screen.
  > ✅ **Fixed:** Created `frontend/components/ChatErrorBoundary.tsx` as a class component implementing `getDerivedStateFromError` and `componentDidCatch`. When triggered, it renders a "Something went wrong" message with a "Try again" button that resets `hasError`. `page.tsx` now wraps `<ChatWindow />` with `<ChatErrorBoundary>`.

- **Show character/length feedback on input:** Since a server-side length limit is recommended, add a subtle counter or disable the send button if the input exceeds the limit.
  > ✅ **Fixed:** A character counter appears below the input when the user reaches 1800 characters (amber) and turns red above 2000. The send button and `handleSend` are both disabled when `inputTooLong` is true. The input border also turns red when over the limit.

---

## AI Improvements

### Parallelization & Async

- **Parallelize semantic vector queries:** In `search_knowledge_base()` (`conversation_agent.py` ~line 88), the up-to-3 semantic queries are run in a synchronous `for` loop. Since each `retriever.invoke()` call is independent, wrap them in `asyncio.gather()` using `retriever.ainvoke()` to run all vector lookups concurrently — this alone can cut retrieval latency by 2–3× when expanded queries are present.
  > ✅ **Fixed:** All semantic queries and the BM25 lookup are now dispatched concurrently in a single `asyncio.gather()` call. Semantic tasks (`active_retriever.ainvoke(q)` for each query) and `bm25.ainvoke(keyword_query)` are built into one list; results are split at `all_results[-1]` for BM25 and `all_results[:-1]` for the semantic batch.
- **Make `search_knowledge_base` fully async:** The function is called with `await` in `nodes.py` but is defined as a plain synchronous function, meaning it blocks the event loop during every retrieval call. Rewrite it as `async def` and replace all `.invoke()` calls with `.ainvoke()` / `asyncio.gather()`.
  > ✅ **Fixed:** `search_knowledge_base` is now `async def`. All `.invoke()` calls are replaced with `.ainvoke()`. The Cohere rerank step (blocking SDK call) is offloaded to the default thread-pool executor via `await loop.run_in_executor(None, lambda: reranker.rerank(...))`. `nodes.py` line 116 updated to `await search_knowledge_base(...)`.
- **Make Pushover notifications async:** The `push()` utility in both `conversation_agent.py` and `contact_agent.py` uses the synchronous `requests.post()`, blocking the event loop inside an `async` node. Replace with `httpx.AsyncClient` and `await client.post(...)` so notifications don't add latency to the response path.
  > ✅ **Fixed:** `integrations/pushover.py` now uses `httpx.AsyncClient` with `await client.post(...)`. Both `record_user_details` in `contact_agent.py` and `record_unknown_question` in `conversation_agent.py` are now `async def` tools that `await push(...)`. The OpenAI Agents SDK natively supports async function tools.

### Streaming

- **Stream the conversation agent response token by token:** The pipeline uses `Runner.run()` and `graph.ainvoke()`, both of which wait for the full response before returning. The OpenAI Agents SDK exposes `Runner.run_streamed()`, and LangGraph exposes `graph.astream()`. Wiring either through the FastAPI `/chat` endpoint as a `StreamingResponse` would dramatically reduce perceived latency — the user sees the first token in ~300–500 ms instead of waiting 2–4 s for the full reply.
  > ⏭️ **Skipped:** Requires full SSE wiring through LangGraph (`graph.astream_events`) and a corresponding frontend streaming consumer. Scope is too large for this revision; deferred to a dedicated streaming iteration.
- **Stream from the conversation node only:** The filter and normalizer nodes are fast structured-output calls and do not benefit from streaming. Only the final `conversation_node` call to `Runner.run_streamed()` needs to yield tokens, keeping the change minimal.
  > ⏭️ **Skipped:** Depends on the full streaming change above.

### Prompt Caching

- **Enable OpenAI prompt caching on the conversation agent:** The `INSTRUCTIONS` string in `conversation_agent.py` is ~450 lines and is sent in full on every turn. OpenAI automatically caches prompt prefixes ≥ 1024 tokens that remain stable across requests. Since `INSTRUCTIONS` never changes between turns, placing it as the first block of the system message (before any dynamic context) lets OpenAI cache it and reduces input token cost and latency by ~50% for the conversation agent call, which is the most expensive step.
  > ✅ **Fixed:** `conversation_agent` now declares `model_settings=ModelSettings(prompt_cache_retention="in_memory")`. The static `INSTRUCTIONS` block is already the first (and only) system message, so it is eligible for caching on every repeated call within a server lifetime.
- **Apply the same pattern to the filter and normalizer agents:** Both `filter_agent.py` and `query_normalizer_agent.py` have long static `INSTRUCTIONS` strings sent on every call. Structuring them as leading, stable system message content enables caching on `gpt-4.1-nano` as well.
  > ✅ **Fixed:** Both agents now declare `model_settings=ModelSettings(temperature=0, max_tokens=500, prompt_cache_retention="in_memory")`. The `max_tokens=500` cap also eliminates over-generation on structured-output calls (see Model & Inference below).

### Pipeline Architecture

- **Merge the filter and normalizer into a single agent call:** Currently `filter_node` calls the filter agent, then `conversation_node` immediately calls the normalizer agent on the same query. Both agents are fast `gpt-4.1-nano` structured-output calls, but each incurs a separate HTTP round-trip (~200–400 ms). A single merged agent that returns both `FilterOutput` and `QueryNormalizedOutput` fields in one structured response would save one full agent call per conversational turn on the info path.
  > ⏭️ **Skipped:** Merging the two agents would require restructuring the LangGraph node routing logic and the `State` model. High regression risk for a moderate latency saving; deferred.
- **Skip LangGraph graph invocation for fast-path invalid queries:** For messages that are clearly invalid (very short, obviously off-topic), the overhead of `graph.ainvoke()` → serializing full state → running LangGraph checkpointing → deserializing result is unnecessary. A lightweight pre-filter before calling `run_superstep` that returns the fixed invalid message directly would shave ~50–100 ms off rejected-query paths.
  > ⏭️ **Skipped:** The filter agent must still run to classify the message; a pre-filter only saves LangGraph overhead on a narrow subset of inputs. Marginal benefit.
- **Reduce retrieved context passed to the conversation agent:** `FILTER_K` and `RETRIEVAL_K` are both 10 (`conversation_agent.py` lines 23–24), meaning up to 10 full documents are formatted and injected into the conversation agent prompt. For a knowledge base of CV-style markdown files, 5 documents is typically sufficient. Reducing `FILTER_K` to 5 directly reduces prompt size and generation latency for the most expensive agent call.
  > ✅ **Fixed:** `FILTER_K` set to 12 in `conversation_agent.py` (up from the original 10). The knowledge base has 54 chunks: experiences = 12 chunks, courses = 10 chunks. `FILTER_K=12` guarantees all experience chunks and all course chunks are passed to the conversation agent on broad queries, preventing entire job roles or courses from being dropped by the reranker cutoff. The `CohereRerank` instance at module level uses `top_n=FILTER_K`.
  >
  > Also fixed a latent bug: `RETRIEVAL_K` was set to 10 but was effectively 4 (Chroma's default) because the global retriever was constructed as `vectorstore.as_retriever()` with no `search_kwargs`, and passing `k=` to `.invoke()` / `.ainvoke()` is silently ignored by LangChain. `RETRIEVAL_K` is now 20 and properly wired into all three retriever constructions: the global `retriever` (`search_kwargs={"k": RETRIEVAL_K}`), the topic-filtered retriever (`search_kwargs={"k": RETRIEVAL_K, "filter": ...}`), and `bm25.k = RETRIEVAL_K` after loading. With 3 semantic queries × 20 = up to 60 candidates (deduped to ~30–40) plus BM25, the reranker now has meaningful competition before selecting the top 12.

### Retrieval

- **Instantiate `CohereRerank` once at module level:** In `search_knowledge_base()`, `CohereRerank(top_n=FILTER_K, model="rerank-english-v3.0")` is constructed on every single retrieval call (`conversation_agent.py` line 132). Object instantiation triggers SDK setup on each invocation. Move it to module level alongside the `bm25` and `vectorstore` singletons.
  > ✅ **Already fixed** in the Backend Improvements pass. `reranker = CohereRerank(top_n=FILTER_K, model="rerank-english-v3.0")` is a module-level singleton.
- **Persist the BM25 index to disk:** `BM25Retriever.from_documents()` iterates and tokenizes the full Chroma corpus on every cold start. Serialize the fitted index with `pickle` during `ingest.py` and deserialize it at startup in `conversation_agent.py`. This eliminates redundant computation on Render restarts and speeds up warmup.
  > ✅ **Already fixed** in the Backend Improvements pass. `ingest.py` serializes the index to `storage/bm25_index.pkl`; `conversation_agent.py` loads it on startup with a fallback rebuild.
- **Use Cohere's async rerank API:** `reranker.rerank()` is a synchronous Cohere API call inside an async function. Use `CohereRerank` with an async client or call `asyncio.get_event_loop().run_in_executor()` to avoid blocking the event loop during the rerank step.
  > ✅ **Fixed:** The rerank call is now dispatched via `await loop.run_in_executor(None, lambda: reranker.rerank(...))` inside the async `search_knowledge_base`, offloading the blocking Cohere SDK call to the default thread-pool executor.

### Model & Inference

- **Reduce `max_tokens` / `temperature` on structured-output agents:** The filter and normalizer agents only need to produce short structured JSON outputs. Explicitly setting a low `max_tokens` (e.g. 300–500) and `temperature=0` in the `Agent(...)` constructor prevents the model from generating unnecessarily long completions and reduces latency for those calls.
  > ✅ **Fixed:** Both `filter_agent` and `query_normalizer_agent` now set `model_settings=ModelSettings(temperature=0, max_tokens=500, prompt_cache_retention="in_memory")`. `temperature=0` ensures deterministic structured outputs; `max_tokens=500` caps generation on calls that never need more than ~200 tokens.
- **Consider `gpt-4.1-nano` for the conversation agent on simple turns:** The conversation agent uses `gpt-4o-mini`. For short factual queries (e.g. "What's your email?") where the retrieved documents are minimal and the answer is a single sentence, routing to `gpt-4.1-nano` would be significantly faster and cheaper. A confidence or complexity score from the filter agent could gate which model is selected per turn.
  > ⏭️ **Skipped:** Requires a confidence/complexity signal from the filter agent and conditional model routing in `conversation_node`. Added complexity without guaranteed quality; deferred.
