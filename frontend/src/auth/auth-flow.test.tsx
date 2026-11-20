import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { clearLocalSession } from "../api/auth"
import { AppRoutes } from "../App"
import { AuthProvider } from "./AuthProvider"

const API_URL = "http://localhost:8000"
const csrfKey = "room-chat.csrf"

function response(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
  })
}

function tokens(access: string, csrf: string) {
  return { access_token: access, csrf_token: csrf, token_type: "bearer", expires_in: 900 }
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider><AppRoutes /></AuthProvider>
    </MemoryRouter>,
  )
}

function mockFetch(implementation: (url: string, init: RequestInit) => Response | Promise<Response>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) =>
    implementation(String(input), init),
  )
  vi.stubGlobal("fetch", fetchMock)
  return fetchMock
}

function requestInitAt(fetchMock: ReturnType<typeof mockFetch>, index: number): RequestInit {
  const call = fetchMock.mock.calls[index]
  if (!call) throw new Error(`Expected fetch call ${index + 1}`)
  return call[1] ?? {}
}

function header(init: RequestInit, name: string): string | null {
  return new Headers(init.headers).get(name)
}

beforeEach(() => {
  clearLocalSession()
  window.sessionStorage.clear()
  window.localStorage.clear()
  document.cookie = "csrf_token=; path=/api/v1/auth; max-age=0"
})

describe("registration", () => {
  it("validates passwords and confirmation before sending a request", async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch(() => response(201, {}))
    renderAt("/register")

    await user.type(screen.getByLabelText("Username"), "alex_user")
    await user.type(screen.getByLabelText("Email address"), "alex@example.com")
    await user.type(screen.getByLabelText("Password"), "short")
    await user.type(screen.getByLabelText("Confirm password"), "different")
    await user.click(screen.getByRole("button", { name: /create account/i }))

    expect(await screen.findByText("Use at least 12 characters.")).toBeInTheDocument()
    expect(screen.getByText("The passwords don’t match.")).toBeInTheDocument()
    expect(fetchMock.mock.calls.some(([url]) => String(url).endsWith("/auth/register"))).toBe(false)
  })

  it("creates an account using the actual registration contract, then asks the user to sign in", async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch((url) => {
      if (url.endsWith("/api/v1/health")) return response(200, { status: "ok" })
      expect(url).toBe(`${API_URL}/api/v1/auth/register`)
      return response(201, {
        id: "2a49edbf-1474-4085-89da-77def2f51b74",
        username: "alex_user",
        email: "alex@example.com",
        is_active: true,
        created_at: "2026-11-20T12:00:00Z",
      })
    })
    renderAt("/register")

    await user.type(screen.getByLabelText("Username"), " Alex_User ")
    await user.type(screen.getByLabelText("Email address"), " Alex@Example.com ")
    await user.type(screen.getByLabelText("Password"), "correct horse battery")
    await user.type(screen.getByLabelText("Confirm password"), "correct horse battery")
    await user.click(screen.getByRole("button", { name: /create account/i }))

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument()
    expect(screen.getByText("Your account is ready. Sign in to continue.")).toBeInTheDocument()
    const registerIndex = fetchMock.mock.calls.findIndex(([url]) => String(url).endsWith("/auth/register"))
    const init = fetchMock.mock.calls[registerIndex]?.[1]
    expect(init?.credentials).toBe("include")
    expect(JSON.parse(String(init?.body))).toEqual({
      username: "alex_user",
      email: "alex@example.com",
      password: "correct horse battery",
    })
    expect(window.localStorage.getItem(csrfKey)).toBeNull()
  })

  it("shows a safe duplicate username/email error", async () => {
    const user = userEvent.setup()
    mockFetch(() => response(409, { detail: "database unique constraint name" }))
    renderAt("/register")

    await user.type(screen.getByLabelText("Username"), "alex_user")
    await user.type(screen.getByLabelText("Email address"), "alex@example.com")
    await user.type(screen.getByLabelText("Password"), "correct horse battery")
    await user.type(screen.getByLabelText("Confirm password"), "correct horse battery")
    await user.click(screen.getByRole("button", { name: /create account/i }))

    expect(await screen.findByRole("alert")).toHaveTextContent("already registered")
    expect(screen.getByRole("alert")).not.toHaveTextContent("constraint")
  })
})

describe("login and routing", () => {
  it("signs in with username/email and holds access credentials only in memory", async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch((url) => {
      if (url.endsWith("/api/v1/health")) return response(200, { status: "ok" })
      expect(url).toBe(`${API_URL}/api/v1/auth/login`)
      return response(200, tokens("access-secret", "csrf-from-login"))
    })
    renderAt("/login")

    await user.type(screen.getByLabelText("Username or email"), "Alex_User")
    await user.type(screen.getByLabelText("Password"), "short-legacy-password")
    await user.click(screen.getByRole("button", { name: /sign in/i }))

    expect(await screen.findByRole("heading", { name: /Make room for/ })).toBeInTheDocument()
    const loginIndex = fetchMock.mock.calls.findIndex(([url]) => String(url).endsWith("/auth/login"))
    const loginInit = requestInitAt(fetchMock, loginIndex)
    expect(JSON.parse(String(loginInit.body))).toEqual({
      username_or_email: "alex_user",
      password: "short-legacy-password",
    })
    expect(loginInit.credentials).toBe("include")
    expect(window.localStorage.getItem(csrfKey)).toBe("csrf-from-login")
    expect(window.localStorage.getItem("access_token")).toBeNull()
    expect(window.sessionStorage.length).toBe(0)
  })

  it("shows generic invalid-credential feedback without backend details", async () => {
    const user = userEvent.setup()
    mockFetch(() => response(401, { detail: "sensitive account lookup details" }))
    renderAt("/login")

    await user.type(screen.getByLabelText("Username or email"), "alex_user")
    await user.type(screen.getByLabelText("Password"), "wrong-password")
    await user.click(screen.getByRole("button", { name: /sign in/i }))

    expect(await screen.findByRole("alert")).toHaveTextContent("don’t match an active account")
    expect(screen.getByRole("alert")).not.toHaveTextContent("lookup")
  })

  it("does not display a protected page before restoration completes", async () => {
    window.localStorage.setItem(csrfKey, "csrf-before-reload")
    let finishRefresh!: (value: Response) => void
    mockFetch(() => new Promise<Response>((resolve) => { finishRefresh = resolve }))
    renderAt("/app")

    expect(screen.getByRole("status")).toHaveTextContent("Restoring your secure session")
    expect(screen.queryByRole("heading", { name: /Make room for/ })).not.toBeInTheDocument()
    finishRefresh(response(401, { detail: "expired" }))
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument()
  })

  it("restores a session through refresh and keeps the access token out of storage", async () => {
    window.localStorage.setItem(csrfKey, "csrf-before-reload")
    const fetchMock = mockFetch((url) => {
      expect(url).toBe(`${API_URL}/api/v1/auth/refresh`)
      return response(200, tokens("restored-access", "csrf-after-refresh"))
    })
    renderAt("/app")

    expect(await screen.findByRole("heading", { name: /Make room for/ })).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const refreshInit = requestInitAt(fetchMock, 0)
    expect(refreshInit.method).toBe("POST")
    expect(refreshInit.credentials).toBe("include")
    expect(header(refreshInit, "X-CSRF-Token")).toBe("csrf-before-reload")
    expect(window.localStorage.getItem(csrfKey)).toBe("csrf-after-refresh")
    expect(window.localStorage.getItem("access_token")).toBeNull()
  })

  it("redirects an unauthenticated visitor away from the protected app", async () => {
    mockFetch(() => response(500, {}))
    renderAt("/app")
    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument()
    expect(screen.queryByRole("heading", { name: /Make room for/ })).not.toBeInTheDocument()
  })
})

describe("refresh and logout", () => {
  async function authenticateAndOpenMenu(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText("Username or email"), "alex_user")
    await user.type(screen.getByLabelText("Password"), "valid-password")
    await user.click(screen.getByRole("button", { name: /sign in/i }))
    await screen.findByRole("heading", { name: /Make room for/ })
    await user.click(screen.getByRole("button", { name: /my account/i }))
  }

  it("refreshes once after an authenticated 401 and retries with the new CSRF value", async () => {
    const user = userEvent.setup()
    let logoutRequests = 0
    let refreshRequests = 0
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith("/auth/login")) return response(200, tokens("access-one", "csrf-one"))
      if (url.endsWith("/auth/logout-all")) {
        logoutRequests += 1
        if (logoutRequests === 1) return response(401, { detail: "expired" })
        expect(header(init, "Authorization")).toBe("Bearer access-two")
        expect(header(init, "X-CSRF-Token")).toBe("csrf-two")
        return response(204)
      }
      if (url.endsWith("/auth/refresh")) {
        refreshRequests += 1
        expect(header(init, "X-CSRF-Token")).toBe("csrf-one")
        return response(200, tokens("access-two", "csrf-two"))
      }
      return response(404, {})
    })
    renderAt("/login")
    await authenticateAndOpenMenu(user)
    await user.click(screen.getByRole("menuitem", { name: /sign out all sessions/i }))

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument()
    expect(logoutRequests).toBe(2)
    expect(refreshRequests).toBe(1)
    expect(fetchMock).toHaveBeenCalledTimes(6)
  })

  it("sends CSRF on logout and clears local auth even when the server fails", async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith("/auth/login")) return response(200, tokens("access-one", "csrf-one"))
      if (url.endsWith("/auth/logout")) {
        expect(init.method).toBe("POST")
        expect(init.credentials).toBe("include")
        expect(header(init, "X-CSRF-Token")).toBe("csrf-one")
        return response(503, { detail: "database connection secret" })
      }
      return response(404, {})
    })
    renderAt("/login")
    await authenticateAndOpenMenu(user)
    await user.click(screen.getByRole("menuitem", { name: /^sign out$/i }))

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument()
    expect(screen.getByText(/You’re signed out on this device/)).toBeInTheDocument()
    expect(window.localStorage.getItem(csrfKey)).toBeNull()
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain("database connection secret")
  })

  it("completes a successful logout and clears local auth", async () => {
    const user = userEvent.setup()
    const fetchMock = mockFetch((url, init) => {
      if (url.endsWith("/auth/login")) return response(200, tokens("access-one", "csrf-one"))
      if (url.endsWith("/auth/logout")) {
        expect(init.method).toBe("POST")
        expect(header(init, "X-CSRF-Token")).toBe("csrf-one")
        return response(204)
      }
      return response(404, {})
    })
    renderAt("/login")
    await authenticateAndOpenMenu(user)
    await user.click(screen.getByRole("menuitem", { name: /^sign out$/i }))

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument()
    expect(screen.getByText("You’re signed out.")).toBeInTheDocument()
    expect(window.localStorage.getItem(csrfKey)).toBeNull()
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it("clears authentication and redirects after a protected request cannot refresh", async () => {
    const user = userEvent.setup()
    window.localStorage.setItem(csrfKey, "csrf-start")
    let refreshRequests = 0
    const fetchMock = mockFetch((url) => {
      if (url.endsWith("/auth/refresh")) {
        refreshRequests += 1
        return refreshRequests === 1
          ? response(200, tokens("access-one", "csrf-one"))
          : response(401, { detail: "private refresh failure" })
      }
      if (url.endsWith("/auth/logout-all")) return response(401, {})
      return response(404, {})
    })
    renderAt("/app")
    await screen.findByRole("heading", { name: /Make room for/ })
    await user.click(screen.getByRole("button", { name: /my account/i }))
    await user.click(screen.getByRole("menuitem", { name: /sign out all sessions/i }))

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument()
    expect(screen.getByText(/You’re signed out on this device/)).toBeInTheDocument()
    expect(window.localStorage.getItem(csrfKey)).toBeNull()
    expect(refreshRequests).toBe(2)
    expect(fetchMock).toHaveBeenCalledTimes(4)
  })

  it("deduplicates simultaneous refresh attempts", async () => {
    window.localStorage.setItem(csrfKey, "csrf-start")
    let protectedRequests = 0
    let refreshRequests = 0
    const fetchMock = mockFetch((url) => {
      if (url.endsWith("/auth/refresh")) {
        refreshRequests += 1
        return response(200, tokens("access-start", "csrf-next"))
      }
      if (url.endsWith("/auth/logout-all")) {
        protectedRequests += 1
        return protectedRequests <= 2 ? response(401, {}) : response(204)
      }
      return response(404, {})
    })
    const { authenticatedRequest } = await import("../api/auth")
    renderAt("/app")
    await screen.findByRole("heading", { name: /Make room for/ })

    await Promise.all([
      authenticatedRequest<void>("/api/v1/auth/logout-all", { method: "POST" }),
      authenticatedRequest<void>("/api/v1/auth/logout-all", { method: "POST" }),
    ])

    expect(refreshRequests).toBe(2) // One initial restore, one shared rotation for both 401s.
    expect(protectedRequests).toBe(4)
    expect(fetchMock).toHaveBeenCalledTimes(6)
  })
})
