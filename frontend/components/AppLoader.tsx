"use client"

import { useEffect, useState } from "react"

export default function AppLoader({
  children,
}: {
  children: React.ReactNode
}) {
  // Tracks whether server is reachable
  const [ready, setReady] = useState(false)

  // Controls UI transition (slightly delayed after ready)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function waitForServer() {
      while (!cancelled) {
        try {
          const res = await fetch("/api/health")

          if (res.ok) {
            setReady(true)
            return
          }
        } catch (err) {
          // ignore errors while warming up
        }

        await new Promise((r) => setTimeout(r, 2000))
      }
    }

    waitForServer()

    return () => {
      cancelled = true
    }
  }, [])

  // Once server is ready, trigger smooth UI transition
  useEffect(() => {
    if (!ready) return

    const t = setTimeout(() => {
      setVisible(true)
    }, 300) // small delay makes fade feel intentional

    return () => clearTimeout(t)
  }, [ready])

  return (
    <div className="relative h-screen w-full overflow-hidden bg-black text-white">

      {/* ================= LOADER LAYER ================= */}
      <div
        className={`
          absolute inset-0 flex items-center justify-center
          transition-opacity duration-500 ease-out
          ${visible ? "opacity-0 pointer-events-none" : "opacity-100"}
        `}
      >
        {/* Background glow (match ChatWindow style) */}
        <div className="absolute top-0 left-0 w-[500px] h-[500px] bg-blue-500/20 blur-[120px] rounded-full" />
        <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-purple-500/20 blur-[120px] rounded-full" />

        {/* Loader content */}
        <div className="relative z-10 flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-white/30 border-t-white" />

          <h1 className="text-lg font-medium">
            Waking up server...
          </h1>

          <p className="text-sm text-neutral-400 text-center max-w-sm">
            Preparing your workspace
          </p>
        </div>
      </div>

      {/* ================= APP LAYER ================= */}
      <div
        className={`
          h-full w-full
          transition-opacity duration-500 ease-out
          ${visible ? "opacity-100" : "opacity-0"}
        `}
      >
        {children}
      </div>
    </div>
  )
}