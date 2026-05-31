"use client";

import { useEffect, useState } from "react";
import { AppReadyContext } from "@/context/AppReadyContext";

const MAX_RETRIES = 4;
const BASE_DELAY_MS = 3000;

async function attemptWarmup(): Promise<boolean> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/warmup`, {
    method: "POST",
  });
  if (!res.ok) return false;
  const data = await res.json();
  return data.status === "ready";
}

export default function AppLoader({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function warmup() {
      for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
        try {
          const ok = await attemptWarmup();
          if (cancelled) return;
          if (ok) {
            setReady(true);
            return;
          }
        } catch {
          if (cancelled) return;
        }

        if (attempt < MAX_RETRIES) {
          const delay = BASE_DELAY_MS * Math.pow(2, attempt);
          await new Promise((r) => setTimeout(r, delay));
          if (cancelled) return;
        }
      }

      if (!cancelled) setError(true);
    }

    warmup();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!ready) return;
    const t = setTimeout(() => setVisible(true), 300);
    return () => clearTimeout(t);
  }, [ready]);

  return (
    <AppReadyContext.Provider value={ready}>
      <div className="relative min-h-dvh w-full bg-black text-white overflow-hidden">

        {/* LOADER overlay */}
        <div
          className={`
            fixed inset-0 z-50 flex items-center justify-center
            bg-black transition-opacity duration-500 ease-out
            ${visible ? "opacity-0 pointer-events-none" : "opacity-100"}
          `}
        >
          {error ? (
            <div className="flex flex-col items-center gap-4 px-6 text-center">
              <p className="text-white/80 text-lg font-medium">
                Unable to connect to the assistant.
              </p>
              <p className="text-white/50 text-sm">
                The server may be unavailable. Please try refreshing.
              </p>
              <button
                onClick={() => window.location.reload()}
                className="mt-2 px-5 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/10 text-sm text-white transition"
              >
                Refresh
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-4">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-white/30 border-t-white" />
              <h1 className="text-lg font-medium text-white/80">
                Warming up...
              </h1>
            </div>
          )}
        </div>

        {/* APP CONTENT */}
        <div
          className={`
            min-h-dvh w-full transition-opacity duration-500 ease-out
            ${visible ? "opacity-100" : "opacity-0"}
          `}
        >
          {children}
        </div>

      </div>
    </AppReadyContext.Provider>
  );
}
