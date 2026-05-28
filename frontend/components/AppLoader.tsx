"use client"

import { useEffect, useState } from "react"

export default function AppLoader({
  children,
}: {
  children: React.ReactNode
}) {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let cancelled = false

    async function wakeServer() {
      while (!cancelled) {
        try {
          const res = await fetch("https://career-conversation-chatbot.onrender.com/health")

          if (res.ok) {
            setReady(true)
            return
          }
        } catch (err) {}

        await new Promise((resolve) => setTimeout(resolve, 2000))
      }
    }

    wakeServer()

    return () => {
      cancelled = true
    }
  }, [])

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-white border-t-transparent" />

          <div className="text-center">
            <h1 className="text-xl font-semibold">
              Waking up server...
            </h1>

            <p className="mt-2 text-sm text-gray-400">
              This may take a few seconds
            </p>
          </div>
        </div>
      </div>
    )
  }

  return <>{children}</>
}