"use client";

import { useEffect, useRef, useState } from "react";
import { streamMessage, WarmingUpError, RateLimitError } from "@/lib/api";
import { v4 as uuidv4 } from "uuid";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { SendHorizonal, User } from "lucide-react";
import remarkGfm from "remark-gfm";
import { useAppReady } from "@/context/AppReadyContext";

const MAX_INPUT_LENGTH = 2000;
const COUNTER_WARN_AT = 1800;

const ANDREU_AVATAR = "/imatge_linkedin.jpg";
const USER_AVATAR = "/alternative_user_avatar2.png";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

function AndreuAvatar({ className }: { className: string }) {
  const [imgFailed, setImgFailed] = useState(false);
  return (
    <div className={`relative ${className} bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center font-bold text-white`}>
      {!imgFailed && (
        <img
          src={ANDREU_AVATAR}
          alt="Andreu"
          className="absolute inset-0 w-full h-full object-cover"
          onError={() => setImgFailed(true)}
        />
      )}
      {imgFailed && <span className="text-sm">AO</span>}
    </div>
  );
}

function UserAvatar({ className }: { className: string }) {
  const [imgFailed, setImgFailed] = useState(false);
  return (
    <div className={`relative ${className} bg-white flex items-center justify-center`}>
      {!imgFailed && (
        <img
          src={USER_AVATAR}
          alt="User"
          className="absolute inset-0 w-full h-full object-cover"
          onError={() => setImgFailed(true)}
        />
      )}
      {imgFailed && <User size={18} className="text-black" />}
    </div>
  );
}

export default function ChatWindow() {
  const appReady = useAppReady();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [waitingForReply, setWaitingForReply] = useState(false);

  const threadIdRef = useRef<string>(uuidv4());
  const bottomRef = useRef<HTMLDivElement>(null);

  // Restore or persist the session threadId across page refreshes
  useEffect(() => {
    try {
      const stored = sessionStorage.getItem("chat_thread_id");
      if (stored) {
        threadIdRef.current = stored;
      } else {
        sessionStorage.setItem("chat_thread_id", threadIdRef.current);
      }
    } catch {
      // sessionStorage unavailable (e.g. private browsing restrictions) — use in-memory ID
    }
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const inputTooLong = input.length > MAX_INPUT_LENGTH;
  const showCounter = input.length >= COUNTER_WARN_AT;

  async function handleSend() {
    if (!input.trim() || loading || inputTooLong || !appReady) return;

    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    const currentInput = input;
    setInput("");
    setLoading(true);
    setWaitingForReply(true);

    // The assistant bubble is created on the first token and updated in place
    const assistantId = uuidv4();
    const setAssistantContent = (update: (content: string) => string) => {
      setWaitingForReply(false);
      setMessages((prev) =>
        prev.some((m) => m.id === assistantId)
          ? prev.map((m) => (m.id === assistantId ? { ...m, content: update(m.content) } : m))
          : [...prev, { id: assistantId, role: "assistant", content: update("") }]
      );
    };

    try {
      let finished = false;

      await streamMessage(currentInput, threadIdRef.current, (event) => {
        if (event.type === "token") {
          setAssistantContent((content) => content + event.content);
        } else if (event.type === "done") {
          finished = true;
          setAssistantContent(() => event.content);
        } else {
          throw new Error("stream_error");
        }
      });

      if (!finished) throw new Error("stream_incomplete");
    } catch (error) {
      let content = "Something went wrong while contacting the chatbot.";
      if (error instanceof WarmingUpError) {
        content = "The assistant is still starting up. Please try again in a few seconds.";
      } else if (error instanceof RateLimitError) {
        content = "You're sending messages too quickly. Please wait a moment before trying again.";
      }
      setAssistantContent(() => content);
    } finally {
      setLoading(false);
      setWaitingForReply(false);
    }
  }

  return (
    <div className="relative h-[100dvh] overflow-hidden overscroll-none bg-black text-white">

      {/* Background Glow Effects */}
      <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-blue-500/20 blur-[120px] rounded-full" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-purple-500/20 blur-[120px] rounded-full" />

      <div className="relative z-10 flex items-center justify-center h-full p-4 md:p-8">

        {/* Main Chat Container */}
        <div
          className="
            w-full h-full mx-2 sm:mx-4 md:mx-6 lg:mx-8
            rounded-2xl sm:rounded-3xl
            border border-white/10
            bg-white/5
            backdrop-blur-2xl
            shadow-2xl
            overflow-hidden
            flex flex-col
          "
        >

          {/* Header */}
          <div className="border-b border-white/10 px-4 sm:px-6 py-3 sm:py-5 bg-black/20 backdrop-blur-xl">
            <div className="flex items-center justify-between gap-3">

              {/* LEFT SIDE: Avatar + title */}
              <div className="flex items-center gap-4">
                <AndreuAvatar className="w-12 h-12 rounded-2xl overflow-hidden shadow-lg shrink-0" />
                <div>
                  <h1 className="text-xl font-semibold tracking-tight">
                    Andreu Ortega AI Assistant
                  </h1>
                  <p className="hidden sm:block text-sm text-neutral-400 mt-1">
                    Ask about Andreu's professional experience, studies, certifications, courses and projects.
                  </p>
                </div>
              </div>

              {/* RIGHT SIDE: LinkedIn */}
              <a
                href="https://www.linkedin.com/in/andreu-ob/"
                target="_blank"
                rel="noopener noreferrer"
                className="
                  flex items-center gap-2 px-3 py-2 rounded-xl
                  bg-white/5 hover:bg-white/10
                  border border-white/10
                  text-sm text-white/80 hover:text-white
                  transition
                "
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1 4.98 2.12 4.98 3.5zM0 8h5v16H0V8zm7.5 0H12v2.2h.1c.6-1.1 2-2.2 4.1-2.2 4.4 0 5.2 2.9 5.2 6.7V24h-5v-7.5c0-1.8 0-4.2-2.6-4.2s-3 2-3 4V24h-5V8z"/>
                </svg>
                <span className="hidden sm:inline">LinkedIn</span>
              </a>

            </div>
          </div>

          {/* Messages */}
          <div className="relative flex-1 min-h-0">

            {/* Top fade shadow */}
            <div className="pointer-events-none absolute top-0 left-0 right-0 h-8 z-10 bg-gradient-to-b from-black/80 to-transparent" />

            {/* Scroll area */}
            <div className="h-full min-h-0 overflow-y-auto overflow-x-hidden no-scrollbar overscroll-y-contain px-4 md:px-8 py-6 space-y-4 sm:space-y-6">

              {/* Empty State */}
              {messages.length === 0 && !loading && (
                <div className="h-full flex flex-col items-center justify-center text-center px-4">
                  <AndreuAvatar className="w-24 h-24 rounded-3xl overflow-hidden shadow-2xl mb-6 text-3xl" />
                  <h2 className="text-4xl font-bold tracking-tight mb-4">Welcome back</h2>
                  <p className="max-w-xl text-neutral-400 leading-relaxed">
                    Ask about Andreu's professional experience, studies, certifications, courses and projects.
                  </p>
                </div>
              )}

              <AnimatePresence>
                {messages.map((message) => (
                  <motion.div
                    key={message.id}
                    initial={{ opacity: 0, y: 20, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.25 }}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`flex gap-3 max-w-[92%] sm:max-w-[80%] ${message.role === "user" ? "flex-row-reverse" : ""}`}>

                      {/* Avatar */}
                      {message.role === "assistant" ? (
                        <AndreuAvatar className="w-10 h-10 rounded-2xl overflow-hidden shrink-0 shadow-lg" />
                      ) : (
                        <UserAvatar className="w-10 h-10 rounded-2xl overflow-hidden shrink-0 shadow-lg" />
                      )}

                      {/* Bubble */}
                      <div className={`
                        rounded-3xl px-4 sm:px-5 py-3 sm:py-4 shadow-xl
                        transition-all duration-300 leading-relaxed
                        ${message.role === "user"
                          ? "bg-gradient-to-r from-blue-500 to-cyan-400 text-white"
                          : "bg-white/10 border border-white/10 backdrop-blur-md text-neutral-100"
                        }
                      `}>
                        <div className="prose prose-invert max-w-none prose-p:my-1 prose-p:leading-snug prose-li:leading-snug prose-strong:text-white leading-snug">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      </div>

                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {waitingForReply && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3"
                >
                  <AndreuAvatar className="w-10 h-10 rounded-2xl overflow-hidden shrink-0" />
                  <div className="bg-white/10 border border-white/10 rounded-3xl px-5 py-4 backdrop-blur-md">
                    <div className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-white animate-bounce" />
                      <span className="w-2 h-2 rounded-full bg-white animate-bounce delay-100" />
                      <span className="w-2 h-2 rounded-full bg-white animate-bounce delay-200" />
                    </div>
                  </div>
                </motion.div>
              )}

              <div ref={bottomRef} />
            </div>

            {/* Bottom fade shadow */}
            <div className="pointer-events-none absolute bottom-0 left-0 right-0 h-10 z-10 bg-gradient-to-t from-black/80 to-transparent" />
          </div>

          {/* Input Area */}
          <div
            className="
              border-t border-white/10
              p-4 md:p-6
              bg-black/20 backdrop-blur-xl
              pb-[calc(env(safe-area-inset-bottom)+12px)]
            "
          >
            <div
              className={`
                w-full mx-auto flex items-center gap-2
                rounded-2xl border bg-white/5
                px-3 sm:px-4 py-3 shadow-lg
                transition-all
                ${inputTooLong
                  ? "border-red-500/60 focus-within:border-red-500"
                  : "border-white/10 focus-within:border-blue-500/50"
                }
              `}
            >
              <div className="relative flex-1 min-w-0">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleSend(); }}
                  placeholder={appReady ? "Ask about Andreu..." : "Warming up..."}
                  disabled={!appReady}
                  className="
                    w-full bg-transparent outline-none
                    text-white placeholder:text-neutral-500
                    disabled:opacity-50 disabled:cursor-not-allowed
                  "
                />
                {showCounter && (
                  <span
                    className={`
                      absolute right-0 -bottom-5 text-xs
                      ${inputTooLong ? "text-red-400" : "text-amber-400"}
                    `}
                  >
                    {input.length}/{MAX_INPUT_LENGTH}
                  </span>
                )}
              </div>

              <button
                onClick={handleSend}
                disabled={loading || inputTooLong || !appReady}
                className="
                  h-11 w-12 shrink-0 rounded-xl
                  bg-gradient-to-r from-blue-500 to-cyan-400
                  flex items-center justify-center shadow-lg
                  hover:scale-105 active:scale-95
                  transition-all duration-200
                  disabled:opacity-50 disabled:hover:scale-100
                "
              >
                <SendHorizonal size={18} />
              </button>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
