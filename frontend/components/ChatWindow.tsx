"use client";

import { useEffect, useRef, useState } from "react";
import { sendMessage } from "@/lib/api";
import { v4 as uuidv4 } from "uuid";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const threadIdRef = useRef(uuidv4());

  async function handleSend() {
    if (!input.trim()) return;

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

      setMessages((prev) => [...prev, assistantMessage]);
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
    <div className="flex flex-col h-screen bg-neutral-950 text-white">
      <div className="border-b border-neutral-800 p-4">
        <h1 className="text-xl font-semibold">
          Andreu Ortega AI Assistant
        </h1>
        <p className="text-sm text-neutral-400 mt-1">
          Ask about career, projects, experience and certifications.
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`max-w-[80%] rounded-2xl px-4 py-3 whitespace-pre-wrap ${
              message.role === "user"
                ? "bg-blue-600 ml-auto"
                : "bg-neutral-800"
            }`}
          >
            {message.content}
          </div>
        ))}

        {loading && (
          <div className="bg-neutral-800 rounded-2xl px-4 py-3 w-fit">
            Thinking...
          </div>
        )}
      </div>
      <div className="border-t border-neutral-800 p-4 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              handleSend();
            }
          }}
          placeholder="Ask something about Andreu Ortega..."
          className="flex-1 bg-neutral-900 border border-neutral-700 rounded-xl px-4 py-3 outline-none"
        />

        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-white text-black px-5 rounded-xl font-medium"
        >
          Send
        </button>
      </div>
    </div>
  );
}