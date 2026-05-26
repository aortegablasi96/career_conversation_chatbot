"use client";

import { useEffect, useRef, useState } from "react";
import { sendMessage } from "@/lib/api";
import { v4 as uuidv4 } from "uuid";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import { SendHorizonal } from "lucide-react";

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
    <div className="relative min-h-screen overflow-hidden bg-black text-white">

      {/* Background Glow Effects */}
      <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-blue-500/20 blur-[120px] rounded-full" />
      <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-purple-500/20 blur-[120px] rounded-full" />

      <div className="relative z-10 flex items-center justify-center min-h-screen p-4 md:p-8">

        {/* Main Chat Container */}
        <div
          className="
            w-full
            max-w-5xl
            h-[92vh]
            rounded-3xl
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
          <div className="border-b border-white/10 px-6 py-5 bg-black/20 backdrop-blur-xl">
            <div className="flex items-center gap-4">

              {/* AI Avatar */}
              <div
                className="
                  w-12
                  h-12
                  rounded-2xl
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
                AI
              </div>

              <div>
                <h1 className="text-xl font-semibold tracking-tight">
                  Andreu Ortega AI Assistant
                </h1>

                <p className="text-sm text-neutral-400 mt-1">
                  Ask about projects, experience,
                  certifications and AI systems.
                </p>
              </div>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">

            {/* Empty State */}
            {messages.length === 0 && !loading && (
              <div className="h-full flex flex-col items-center justify-center text-center px-4">

                <div
                  className="
                    w-24
                    h-24
                    rounded-3xl
                    bg-gradient-to-br
                    from-blue-500
                    to-purple-500
                    flex
                    items-center
                    justify-center
                    text-3xl
                    font-bold
                    mb-6
                    shadow-2xl
                  "
                >
                  AI
                </div>

                <h2 className="text-4xl font-bold tracking-tight mb-4">
                  Welcome back
                </h2>

                <p className="max-w-xl text-neutral-400 leading-relaxed">
                  Ask anything about Andreu Ortega’s
                  projects, frontend engineering,
                  AI integrations, certifications,
                  or professional experience.
                </p>
              </div>
            )}

            <AnimatePresence>
              {messages.map((message, index) => (
                <motion.div
                  key={index}
                  initial={{
                    opacity: 0,
                    y: 20,
                    scale: 0.98,
                  }}
                  animate={{
                    opacity: 1,
                    y: 0,
                    scale: 1,
                  }}
                  transition={{
                    duration: 0.25,
                  }}
                  className={`flex ${
                    message.role === "user"
                      ? "justify-end"
                      : "justify-start"
                  }`}
                >
                  <div
                    className={`
                      flex
                      gap-3
                      max-w-[85%]
                      ${
                        message.role === "user"
                          ? "flex-row-reverse"
                          : ""
                      }
                    `}
                  >

                    {/* Avatar */}
                    <div
                      className={`
                        w-10
                        h-10
                        rounded-2xl
                        flex
                        items-center
                        justify-center
                        text-sm
                        font-semibold
                        shrink-0
                        shadow-lg
                        ${
                          message.role === "user"
                            ? "bg-white text-black"
                            : "bg-gradient-to-br from-blue-500 to-purple-500"
                        }
                      `}
                    >
                      {message.role === "user"
                        ? "Y"
                        : "AI"}
                    </div>

                    {/* Bubble */}
                    <div
                      className={`
                        rounded-3xl
                        px-5
                        py-4
                        shadow-xl
                        whitespace-pre-wrap
                        transition-all
                        duration-300
                        leading-relaxed
                        ${
                          message.role === "user"
                            ? `
                              bg-gradient-to-r
                              from-blue-500
                              to-cyan-400
                              text-white
                            `
                            : `
                              bg-white/10
                              border
                              border-white/10
                              backdrop-blur-md
                              text-neutral-100
                            `
                        }
                      `}
                    >
                      <div className="prose prose-invert max-w-none prose-p:leading-relaxed">
                        <ReactMarkdown>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Loading Indicator */}
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-3"
              >
                <div
                  className="
                    w-10
                    h-10
                    rounded-2xl
                    bg-gradient-to-br
                    from-blue-500
                    to-purple-500
                    flex
                    items-center
                    justify-center
                    text-sm
                    font-semibold
                  "
                >
                  AI
                </div>

                <div
                  className="
                    bg-white/10
                    border
                    border-white/10
                    rounded-3xl
                    px-5
                    py-4
                    backdrop-blur-md
                  "
                >
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

          {/* Input Area */}
          <div
            className="
              border-t
              border-white/10
              p-4
              md:p-6
              bg-black/20
              backdrop-blur-xl
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