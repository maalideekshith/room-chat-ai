import { useEffect, useState } from "react"

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"

type HealthStatus = "loading" | "connected" | "unavailable"

export default function App() {
  const [status, setStatus] = useState<HealthStatus>("loading")

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE_URL}/api/v1/health`)
      .then((res) => {
        if (!res.ok) throw new Error("unhealthy")
        return res.json()
      })
      .then(() => {
        if (!cancelled) setStatus("connected")
      })
      .catch(() => {
        if (!cancelled) setStatus("unavailable")
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 flex items-center justify-center">
      <section className="max-w-md text-center space-y-4 p-8">
        <h1 className="text-3xl font-bold">Room Chat AI</h1>
        <p className="text-slate-600">Modular monolith chat platform - Day 1</p>
        {status === "loading" && <p className="text-slate-500">Checking backend...</p>}
        {status === "connected" && <p className="text-green-600 font-medium">Backend connected</p>}
        {status === "unavailable" && <p className="text-red-600 font-medium">Backend unavailable</p>}
      </section>
    </main>
  )
}
