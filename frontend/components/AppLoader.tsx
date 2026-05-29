"use client";

import { useEffect, useState } from "react";

export default function AppLoader({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function warmup() {
      try {
        const res = await fetch(
          "https://career-conversation-chatbot.onrender.com/warmup",
          { method: "POST" }
        );

        if (!res.ok) return;

        const data = await res.json();

        if (!cancelled && data.status === "ready") {
          setReady(true);
        }
      } catch {
        // optional retry logic
      }
    }

    warmup();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!ready) return;

    const t = setTimeout(() => {
      setVisible(true);
    }, 300);

    return () => clearTimeout(t);
  }, [ready]);

  return (
    <div className="relative min-h-dvh w-full bg-black text-white overflow-hidden">

      {/* LOADER (does NOT affect layout flow) */}
      <div
        className={`
          fixed inset-0 z-50 flex items-center justify-center
          bg-black transition-opacity duration-500 ease-out
          ${visible ? "opacity-0 pointer-events-none" : "opacity-100"}
        `}
      >
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-white/30 border-t-white" />
          <h1 className="text-lg font-medium text-white/80">
            Warming up...
          </h1>
        </div>
      </div>

      {/* APP CONTENT (always stable underneath) */}
      <div
        className={`
          min-h-dvh w-full transition-opacity duration-500 ease-out
          ${visible ? "opacity-100" : "opacity-0"}
        `}
      >
        {children}
      </div>

    </div>
  );
}