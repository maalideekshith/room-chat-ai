import { fireEvent, render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { clearLocalSession } from "../api/auth"
import { AppRoutes } from "../App"
import { AuthProvider } from "../auth/AuthProvider"
import type { Conversation, Credential, Message } from "../api/solo"

const csrfKey = "room-chat.csrf"
const authTokens = { access_token: "access-only-memory", csrf_token: "csrf-rotated", token_type: "bearer", expires_in: 900 }
const credential: Credential = {
  id: "cred-1", provider: "openai", label: "Personal OpenAI", key_suffix: "4321",
  status: "active", last_validated_at: "2026-11-21T10:00:00Z", created_at: "2026-11-21T10:00:00Z",
}

function response(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
  })
}

function convo(id: string, title: string): Conversation {
  return {
    id, title, provider: null, credential_id: null, model: null,
    created_at: "2026-11-21T10:00:00Z", updated_at: "2026-11-21T10:00:00Z",
  }
}

function message(id: string, conversationId: string, role: "user" | "assistant", content: string): Message {
  return {
    id, conversation_id: conversationId, role, content, source_refs: [],
    created_at: "2026-11-21T10:01:00Z",
  }
}

function setupWorkspace(
  implementation: (path: string, init: RequestInit) => Response | Promise<Response>,
) {
  window.localStorage.setItem(csrfKey, "csrf-before-refresh")
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) =>
    implementation(new URL(String(input)).pathname, init),
  )
  vi.stubGlobal("fetch", fetchMock)
  render(<MemoryRouter initialEntries={["/app/room"]}><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter>)
  return fetchMock
}

function baseResponse(path: string): Response | undefined {
  if (path.endsWith("/auth/refresh")) return response(200, authTokens)
  if (path === "/api/v1/solo/conversations") return response(200, [])
  if (path === "/api/v1/solo/credentials") return response(200, [])
  if (path === "/api/v1/solo/providers") return response(200, { providers: [{ id: "openai" }, { id: "anthropic" }, { id: "gemini" }] })
  if (path === "/api/v1/solo/preferences") return response(200, { provider: null, credential_id: null, model: null })
  if (path === "/api/v1/solo/sources") return response(200, [])
  return undefined
}

beforeEach(() => {
  clearLocalSession()
  window.localStorage.clear()
  window.sessionStorage.clear()
})

describe("Solo workspace", () => {
  it("renders the private first-use state and knowledge empty state", async () => {
    setupWorkspace((path) => baseResponse(path) ?? response(404, {}))
    expect(await screen.findByRole("heading", { name: /Make room for/ })).toBeInTheDocument()
    expect(screen.getByText(/Connect your own provider key/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: /Knowledge sources/ }))
    expect(await screen.findByRole("heading", { name: "No sources yet" })).toBeInTheDocument()
    expect(screen.getByText(/Only you can access these files/)).toBeInTheDocument()
  })

  it("creates a conversation, sends a message, and shows the stored reply", async () => {
    const user = userEvent.setup()
    let conversations: Conversation[] = []
    let stored: Message[] = []
    const fetchMock = setupWorkspace((path, init) => {
      if (path === "/api/v1/solo/conversations" && init.method === "POST") {
        const created = convo("conversation-1", "New conversation")
        conversations = [created]
        return response(201, created)
      }
      if (path === "/api/v1/solo/conversations") return response(200, conversations)
      if (path === "/api/v1/solo/credentials") return response(200, [credential])
      const base = baseResponse(path)
      if (base) return base
      if (path === `/api/v1/solo/credentials/${credential.id}/models`) return response(200, { models: ["gpt-4.1-mini"] })
      if (path === "/api/v1/solo/conversations/conversation-1/ai-settings" && init.method === "PUT") {
        return response(200, { ...convo("conversation-1", "New conversation"), provider: "openai", credential_id: credential.id, model: "gpt-4.1-mini" })
      }
      if (path === "/api/v1/solo/conversations/conversation-1/messages" && init.method === "POST") {
        const body = JSON.parse(String(init.body)) as { content: string }
        stored = [message("user-1", "conversation-1", "user", body.content), message("assistant-1", "conversation-1", "assistant", "A useful answer.")]
        return response(201, stored)
      }
      if (path === "/api/v1/solo/conversations/conversation-1/messages") return response(200, stored)
      return response(404, {})
    })
    expect(await screen.findByRole("heading", { name: /Make room for/ })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /New conversation/ }))
    expect(await screen.findByRole("heading", { name: "What are you working on?" })).toBeInTheDocument()
    await user.selectOptions(screen.getByRole("combobox", { name: "Conversation model" }), "openai|cred-1|gpt-4.1-mini")
    const composer = screen.getByRole("textbox", { name: "Message Room Chat AI" })
    await user.type(composer, "Summarize the decision")
    await user.click(screen.getByRole("button", { name: "Send message" }))
    expect(await screen.findByText("A useful answer.")).toBeInTheDocument()
    expect(screen.getByText("Summarize the decision")).toBeInTheDocument()
    const sendCall = fetchMock.mock.calls.find(([input, init]) =>
      new URL(String(input)).pathname.endsWith("/messages") && init?.method === "POST",
    )
    expect(sendCall).toBeDefined()
    expect(new Headers(sendCall?.[1]?.headers).get("X-CSRF-Token")).toBe("csrf-rotated")
  })

  it("switches conversation history without carrying the previous messages across", async () => {
    const first = convo("conversation-1", "First topic")
    const second = convo("conversation-2", "Second topic")
    setupWorkspace((path) => {
      const base = baseResponse(path)
      if (base) return path === "/api/v1/solo/conversations" ? response(200, [first, second]) : base
      if (path.endsWith("/conversation-1/messages")) return response(200, [message("m1", first.id, "assistant", "First history")])
      if (path.endsWith("/conversation-2/messages")) return response(200, [message("m2", second.id, "assistant", "Second history")])
      return response(404, {})
    })
    expect(await screen.findByText("First history")).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole("button", { name: /Second topic/ })[0])
    expect(await screen.findByText("Second history")).toBeInTheDocument()
    expect(screen.queryByText("First history")).not.toBeInTheDocument()
  })

  it("keeps failed requests generic and reloads the persisted user message", async () => {
    const existing = convo("conversation-1", "Research question")
    let posted = false
    setupWorkspace((path, init) => {
      if (path === "/api/v1/solo/credentials") return response(200, [credential])
      const base = baseResponse(path)
      if (base) return path === "/api/v1/solo/conversations" ? response(200, [existing]) : base
      if (path === `/api/v1/solo/credentials/${credential.id}/models`) return response(200, { models: ["gpt-4.1-mini"] })
      if (path.endsWith("/ai-settings") && init.method === "PUT") return response(200, { ...existing, provider: "openai", credential_id: credential.id, model: "gpt-4.1-mini" })
      if (path.endsWith("/messages") && init.method === "POST") { posted = true; return response(502, { detail: "provider secret or internal trace" }) }
      if (path.endsWith("/messages")) return response(200, posted ? [message("user-1", existing.id, "user", "Keep my question")] : [])
      return response(404, {})
    })
    await screen.findByRole("textbox", { name: "Message Room Chat AI" })
    const user = userEvent.setup()
    await user.selectOptions(screen.getByRole("combobox", { name: "Conversation model" }), "openai|cred-1|gpt-4.1-mini")
    await user.type(screen.getByRole("textbox", { name: "Message Room Chat AI" }), "Keep my question")
    await user.click(screen.getByRole("button", { name: "Send message" }))
    expect(await screen.findByText("Keep my question")).toBeInTheDocument()
    expect(await screen.findByRole("alert")).toHaveTextContent("trouble right now")
    expect(screen.getByRole("alert")).not.toHaveTextContent("internal trace")
  })

  it("uploads a supported source as multipart without storing provider credentials", async () => {
    const user = userEvent.setup()
    const source = {
      id: "source-1", kind: "file", title: "notes.md", url: null, mime_type: "text/markdown",
      size_bytes: 18, status: "ready", error_code: null, created_at: "2026-11-21T10:00:00Z", processed_at: "2026-11-21T10:01:00Z",
    }
    const fetchMock = setupWorkspace((path, init) => {
      const base = baseResponse(path)
      if (base) return path === "/api/v1/solo/sources" ? response(200, []) : base
      if (path === "/api/v1/solo/sources/files" && init.method === "POST") return response(201, source)
      return response(404, {})
    })
    await user.click(await screen.findByRole("button", { name: /Knowledge sources/ }))
    const file = new File(["# Useful notes"], "notes.md", { type: "text/markdown" })
    fireEvent.change(screen.getByLabelText("Upload a document", { selector: "input" }), { target: { files: [file] } })
    expect(await screen.findByText("notes.md")).toBeInTheDocument()
    const uploadCall = fetchMock.mock.calls.find(([input]) => new URL(String(input)).pathname.endsWith("/sources/files"))
    expect(uploadCall?.[1]?.body).toBeInstanceOf(FormData)
    expect(new Headers(uploadCall?.[1]?.headers).has("Content-Type")).toBe(false)
    expect(window.localStorage.getItem("access_token")).toBeNull()
    expect(window.localStorage.getItem("provider_key")).toBeNull()
  })
})
