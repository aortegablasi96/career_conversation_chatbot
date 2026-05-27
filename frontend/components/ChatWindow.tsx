"use client";

import { useEffect, useRef, useState } from "react";
import { sendMessage } from "@/lib/api";
import { v4 as uuidv4 } from "uuid";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { SendHorizonal } from "lucide-react";
import remarkGfm from "remark-gfm";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const threadIdRef = useRef(uuidv4());
  const bottomRef = useRef<HTMLDivElement>(null);

  const ANDREU_AVATAR = "/imatge_linkedin.jpg"
  const USER_AVATAR = "/alternative_user_avatar2.png"

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, loading]);

  async function handleSend() {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);

    const currentInput = input;
    setInput("");
    setLoading(true);

    try {
      const response = await sendMessage(
        currentInput,
        threadIdRef.current
      );

      const assistantMessage: Message = {
        role: "assistant",
        content: response.reply,
      };

      setMessages((prev) => [
        ...prev,
        assistantMessage,
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Something went wrong while contacting the chatbot.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative h-[100dvh] overflow-hidden bg-black text-white">

      {/* Background Glow Effects */}
      <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-blue-500/20 blur-[120px] rounded-full" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-purple-500/20 blur-[120px] rounded-full" />

      <div className="relative z-10 flex items-center justify-center h-full p-4 md:p-8">

        {/* Main Chat Container */}
        <div
          className="
            w-full
            h-full
            mx-2
            sm:mx-4
            md:mx-6
            lg:mx-8

            rounded-2xl
            sm:rounded-3xl

            border border-white/10
            bg-white/5
            backdrop-blur-2xl
            shadow-2xl
            overflow-hidden
            flex
            flex-col
          "
        >

          {/* Header */}
          <div className="border-b border-white/10 px-4 sm:px-6 py-3 sm:py-5 bg-black/20 backdrop-blur-xl">
            
            <div className="flex items-center justify-between gap-3">

              {/* LEFT SIDE: Avatar */}
              <div className="flex items-center gap-4">

                {/* AI Avatar */}
                <div
                  className="
                    w-12
                    h-12
                    rounded-2xl
                    overflow-hidden
                    bg-gradient-to-br
                    from-blue-500
                    to-purple-500
                    flex
                    items-center
                    justify-center
                    font-bold
                    text-lg
                    shadow-lg
                  "
                >
                  <img
                    src={ANDREU_AVATAR}
                    alt="Andreu"
                    className="w-full h-full object-cover"
                  />
                </div>

                <div>
                  <h1 className="text-xl font-semibold tracking-tight">
                    Andreu Ortega AI Assistant
                  </h1>

                  <p className="hidden sm:block text-sm text-neutral-400 mt-1">
                    Ask about Andreu's professional experience, studies, certifications, courses and projects.
                  </p>
                </div>
              </div>

              {/* RIGHT SIDE: Linkedin*/}
              <a
                href="https://www.linkedin.com/in/andreu-ob/"
                target="_blank"
                rel="noopener noreferrer"
                className="
                  flex
                  items-center
                  gap-2
                  px-3
                  py-2
                  rounded-xl
                  bg-white/5
                  hover:bg-white/10
                  border
                  border-white/10
                  text-sm
                  text-white/80
                  hover:text-white
                  transition
                "
              >
                {/* LinkedIn Icon */}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
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
            <div className="h-full overflow-y-auto no-scrollbar overscroll-contain px-4 md:px-8 py-6 space-y-4 sm:space-y-6">
              
              {/* Empty State */}
              {messages.length === 0 && !loading && (
                <div className="h-full flex flex-col items-center justify-center text-center px-4">
                  <div className="
                    w-24 h-24 rounded-3xl overflow-hidden
                    bg-gradient-to-br from-blue-500 to-purple-500
                    flex items-center justify-center
                    text-3xl font-bold mb-6 shadow-2xl
                  ">
                    <img
                      src={ANDREU_AVATAR}
                      alt="Andreu"
                      className="w-full h-full object-cover"
                    />
                  </div>

                  <h2 className="text-4xl font-bold tracking-tight mb-4">
                    Welcome back
                  </h2>

                  <p className="max-w-xl text-neutral-400 leading-relaxed">
                    Ask about Andreu's professional experience, studies, certifications, courses and projects.
                  </p>
                </div>
              )}

              <AnimatePresence>
                {messages.map((message, index) => (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 20, scale: 0.98 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ duration: 0.25 }}
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div className={`flex gap-3 max-w-[92%] sm:max-w-[80%] ${
                      message.role === "user" ? "flex-row-reverse" : ""
                    }`}>

                      {/* Avatar */}
                      <div
                        className={`
                          w-10 h-10 rounded-2xl overflow-hidden
                          flex items-center justify-center
                          shrink-0 shadow-lg
                          ${message.role === "user"
                            ? "bg-white"
                            : "bg-gradient-to-br from-blue-500 to-purple-500"
                          }
                        `}
                      >
                        <img
                          src={
                            message.role === "user"
                              ? USER_AVATAR
                              : ANDREU_AVATAR
                          }
                          alt="avatar"
                          className="w-full h-full object-cover"
                        />
                      </div>
                      {/* Bubble */}
                      <div className={`
                        rounded-3xl px-4 sm:px-5 py-3 sm:py-4 shadow-xl
                        transition-all duration-300
                        leading-relaxed
                        ${message.role === "user"
                          ? "bg-gradient-to-r from-blue-500 to-cyan-400 text-white"
                          : "bg-white/10 border border-white/10 backdrop-blur-md text-neutral-100"
                        }
                      `}>
                        <div className="
                          prose prose-invert max-w-none
                          prose-p:my-1
                          prose-p:leading-snug
                          prose-li:leading-snug
                          prose-strong:text-white
                          leading-snug
                        ">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>

              {loading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex items-center gap-3"
                >
                  <div className="w-10 h-10 rounded-2xl overflow-hidden bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-sm font-semibold">
                    <img
                      src={ANDREU_AVATAR}
                      alt="Andreu"
                      className="w-full h-full object-cover"
                    />
                  </div>

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

              sticky bottom-0
              pb-[env(safe-area-inset-bottom)]
            "
          >
            <div
              className="
                flex
                items-center
                gap-3
                rounded-2xl
                border
                border-white/10
                bg-white/5
                px-4
                py-3
                shadow-lg
                focus-within:border-blue-500/50
                transition-all
              "
            >
              <input
                value={input}
                onChange={(e) =>
                  setInput(e.target.value)
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    handleSend();
                  }
                }}
                placeholder="Ask something about Andreu Ortega..."
                className="
                  flex-1
                  bg-transparent
                  outline-none
                  text-white
                  placeholder:text-neutral-500
                "
              />

              <button
                onClick={handleSend}
                disabled={loading}
                className="
                  h-11
                  w-11
                  rounded-xl
                  bg-gradient-to-r
                  from-blue-500
                  to-cyan-400
                  flex
                  items-center
                  justify-center
                  shadow-lg
                  hover:scale-105
                  active:scale-95
                  transition-all
                  duration-200
                  disabled:opacity-50
                  disabled:hover:scale-100
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