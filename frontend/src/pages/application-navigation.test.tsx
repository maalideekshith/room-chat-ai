import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, useNavigate } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { clearLocalSession } from "../api/auth"
import { AppRoutes } from "../App"
import { AuthProvider } from "../auth/AuthProvider"
import type { Conversation } from "../api/solo"

const csrfKey = "room-chat.csrf"
const tokens = {
  access_token: "navigation-test-access",
  csrf_token: "navigation-test-csrf",
  token_type: "bearer",
  expires_in: 900,
}

function response(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
  })
}

function conversation(id: string): Conversation {
  const now = "2026-11-21T10:00:00Z"
  return {
    id, title: "New conversation", provider: null, credential_id: null, model: null,
    created_at: now, updated_at: now,
  }
}

function RouterHistoryControls() {
  const navigate = useNavigate()
  return <div><button type="button" onClick={() => navigate(-1)}>Go back in history</button><button type="button" onClick={() => navigate(1)}>Go forward in history</button></div>
}

function renderApplication(showHistoryControls = false) {
  window.localStorage.setItem(csrfKey, "before-restore")
  let conversations: Conversation[] = []
  let roomMessageLoads = 0
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const path = new URL(String(input)).pathname
    if (path.endsWith("/auth/refresh")) return response(200, tokens)
    if (path === "/api/v1/solo/conversations" && init.method === "POST") {
      conversations = [conversation("room-conversation-1"), ...conversations]
      return response(201, conversations[0])
    }
    if (path === "/api/v1/solo/conversations") return response(200, conversations)
    if (path === "/api/v1/solo/credentials") return response(200, [])
    if (path === "/api/v1/solo/providers") return response(200, { providers: [] })
    if (path === "/api/v1/solo/preferences") return response(200, { provider: null, credential_id: null, model: null })
    if (path === "/api/v1/solo/sources") return response(200, [])
    if (path === "/api/v1/solo/conversations/room-conversation-1/messages") {
      roomMessageLoads += 1
      return response(200, roomMessageLoads > 1 ? [{
        id: "room-message-1", conversation_id: "room-conversation-1", role: "assistant",
        content: "Loaded existing Room conversation", source_refs: [], created_at: "2026-11-21T10:01:00Z",
      }] : [])
    }
    if (path.endsWith("/messages")) return response(200, [])
    return response(404, {})
  })
  vi.stubGlobal("fetch", fetchMock)
  render(<MemoryRouter initialEntries={["/app"]}><AuthProvider>{showHistoryControls && <RouterHistoryControls />}<AppRoutes /></AuthProvider></MemoryRouter>)
  return fetchMock
}

beforeEach(() => {
  clearLocalSession()
  window.localStorage.clear()
  window.sessionStorage.clear()
})

describe("main application navigation", () => {
  it("has exactly four primary destinations and a separate Settings destination", async () => {
    const user = userEvent.setup()
    const fetchMock = renderApplication()
    expect(await screen.findByRole("heading", { name: "Welcome to Room Chat AI" })).toBeInTheDocument()
    const overviewHeader = screen.getByRole("banner")
    expect(overviewHeader.querySelector(".app-topbar-brand")).not.toBeInTheDocument()
    expect(overviewHeader.querySelector(".topbar-crumb")).not.toBeInTheDocument()
    expect(overviewHeader.querySelector(".mobile-menu-button")).not.toBeInTheDocument()
    expect(overviewHeader.children).toHaveLength(1)
    expect(screen.getByRole("button", { name: "My account" })).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Open application navigation" })).not.toBeInTheDocument()
    expect(screen.queryByText("Recent conversations")).not.toBeInTheDocument()
    expect(document.querySelector(".topbar-crumb")).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([input]) => new URL(String(input)).pathname === "/api/v1/solo/conversations")).toBe(false)

    const primary = screen.getByRole("navigation", { name: "Primary navigation" })
    expect(within(primary).getAllByRole("link").map((link) => link.textContent?.trim())).toEqual([
      "Overview", "Room", "Team Room", "Chat",
    ])
    const settings = screen.getByRole("navigation", { name: "Application settings" })
    expect(within(settings).getAllByRole("link").map((link) => link.textContent?.trim())).toEqual(["Settings"])
    expect(primary.compareDocumentPosition(settings) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    const brandName = document.querySelector(".sidebar__brand .brand__wordmark")
    expect(brandName?.textContent?.replace(/\s+/g, " ").trim()).toBe("Room Chat AI")
    expect(brandName?.children).toHaveLength(0)
    expect(within(primary).getByRole("link", { name: "Room" }).querySelector(".room-nav-glyph")).toBeInTheDocument()
    expect(document.querySelector('a.overview-space-card[href="/app/room"] .room-card-glyph')).toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Open Room/ }).querySelector(".room-cta-glyph")).toBeInTheDocument()

    await user.click(within(primary).getByRole("link", { name: "Team Room" }))
    expect(await screen.findByRole("heading", { name: "Team Room" })).toBeInTheDocument()
    expect(screen.getByText(/No room, membership or invitation has been created/)).toBeInTheDocument()

    await user.click(within(primary).getByRole("link", { name: "Chat" }))
    expect(await screen.findByRole("heading", { name: "Chat" })).toBeInTheDocument()
    expect(screen.getByText(/Messages will not be sent or stored here/)).toBeInTheDocument()

    await user.click(within(settings).getByRole("link", { name: "Settings" }))
    expect(await screen.findByRole("heading", { name: "Settings" })).toBeInTheDocument()
    await user.click(screen.getByRole("link", { name: /Manage providers/ }))
    expect(await screen.findByRole("heading", { name: "AI providers" })).toBeInTheDocument()
  })

  it("opens the existing Room workspace and preserves conversation creation and history", async () => {
    const user = userEvent.setup()
    const fetchMock = renderApplication()
    const primary = await screen.findByRole("navigation", { name: "Primary navigation" })

    await user.click(within(primary).getByRole("link", { name: "Room" }))
    expect(await screen.findByRole("heading", { name: /Make room for/ })).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: "Solo workspace" })).toBeInTheDocument()
    expect(screen.queryByRole("navigation", { name: "Primary navigation" })).not.toBeInTheDocument()
    expect(screen.getByRole("link", { name: /Back to Overview/ })).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: /New conversation/ }))
    expect(await screen.findByRole("heading", { name: "What are you working on?" })).toBeInTheDocument()

    await user.click(screen.getByRole("link", { name: /Back to Overview/ }))
    expect(await screen.findByRole("heading", { name: "Welcome to Room Chat AI" })).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument()
    await user.click(within(screen.getByRole("navigation", { name: "Primary navigation" })).getByRole("link", { name: "Room" }))
    expect(await screen.findByText("Loaded existing Room conversation")).toBeInTheDocument()
    expect(screen.queryByRole("navigation", { name: "Primary navigation" })).not.toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([input, init]) =>
      new URL(String(input)).pathname === "/api/v1/solo/conversations" && init?.method === "POST",
    )).toBe(true)
  })

  it("uses application route history for browser back and forward", async () => {
    const user = userEvent.setup()
    renderApplication(true)
    const primary = await screen.findByRole("navigation", { name: "Primary navigation" })
    await user.click(within(primary).getByRole("link", { name: "Room" }))
    expect(await screen.findByRole("heading", { name: /Make room for/ })).toBeInTheDocument()
    expect(screen.queryByRole("navigation", { name: "Primary navigation" })).not.toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Go back in history" }))
    expect(await screen.findByRole("heading", { name: "Welcome to Room Chat AI" })).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Go forward in history" }))
    expect(await screen.findByRole("heading", { name: /Make room for/ })).toBeInTheDocument()
    expect(screen.queryByRole("navigation", { name: "Primary navigation" })).not.toBeInTheDocument()
  })

  it("keeps mobile Overview navigation accessible without a header menu", async () => {
    const user = userEvent.setup()
    renderApplication()
    expect(await screen.findByRole("heading", { name: "Welcome to Room Chat AI" })).toBeInTheDocument()

    expect(screen.queryByRole("button", { name: "Open application navigation" })).not.toBeInTheDocument()
    const mobileNavigation = screen.getByRole("navigation", { name: "Mobile primary navigation" })
    expect(within(mobileNavigation).getByRole("link", { name: "Settings" })).toBeInTheDocument()
    await user.click(within(mobileNavigation).getByRole("link", { name: "Chat" }))
    expect(await screen.findByRole("heading", { name: "Chat" })).toBeInTheDocument()
    expect(screen.queryByRole("complementary", { name: "Application navigation" })).not.toBeInTheDocument()
  })
})
