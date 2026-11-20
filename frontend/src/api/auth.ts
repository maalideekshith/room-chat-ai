export interface RegisterPayload {
  username: string
  email: string
  password: string
}

export interface RegisteredUser {
  id: string
  username: string
  email: string
  is_active: boolean
  created_at: string
}

export interface LoginPayload {
  username_or_email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  csrf_token: string
  token_type: "bearer"
  expires_in: number
}

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = "ApiError"
  }
}

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "")
const csrfStorageKey = "room-chat.csrf"
const csrfCookieName = "csrf_token"
const csrfHeaderName = "X-CSRF-Token"

let accessToken: string | null = null
let csrfToken: string | null = null
let refreshInFlight: Promise<boolean> | null = null
let restorationInFlight: Promise<boolean> | null = null

function readStoredCsrf(): string | null {
  try {
    const stored = window.localStorage.getItem(csrfStorageKey)
    if (stored) {
      csrfToken = stored
      return csrfToken
    }
    csrfToken = null
  } catch {
    // Fall back to the in-memory value when browser storage is unavailable.
  }
  if (csrfToken) return csrfToken

  const cookie = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${csrfCookieName}=`))
  if (!cookie) return null

  try {
    csrfToken = decodeURIComponent(cookie.slice(csrfCookieName.length + 1))
    return csrfToken
  } catch {
    return null
  }
}

function saveTokens(payload: TokenResponse): void {
  accessToken = payload.access_token
  csrfToken = payload.csrf_token
  try {
    // The API also sets this JS-readable double-submit cookie; this copy is not an authentication credential.
    window.localStorage.setItem(csrfStorageKey, csrfToken)
  } catch {
    // Keep the CSRF value in memory for this page if storage is unavailable.
  }
}

export function clearLocalSession(): void {
  accessToken = null
  csrfToken = null
  try {
    window.localStorage.removeItem(csrfStorageKey)
  } catch {
    // Authentication state is still cleared from memory.
  }
}

function notifySessionExpired(): void {
  clearLocalSession()
  window.dispatchEvent(new CustomEvent("roomchat:auth-expired"))
}

function userMessage(status: number): string {
  if (status === 401) return "Your session is no longer valid. Please sign in again."
  if (status === 403) return "This request could not be verified. Refresh the page and try again."
  if (status === 409) return "That username or email is already registered. Try signing in or choose another."
  if (status === 422) return "Please check the information and try again."
  if (status >= 500) return "Room Chat AI is having trouble right now. Please try again shortly."
  return "We couldn’t complete that request. Please try again."
}

async function send(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json")
  try {
    return await fetch(`${apiBaseUrl}${path}`, {
      ...init,
      headers,
      credentials: "include",
      cache: "no-store",
    })
  } catch {
    throw new ApiError(0, "We couldn’t reach Room Chat AI. Check your connection and try again.")
  }
}

async function jsonRequest<T>(path: string, init: RequestInit): Promise<T> {
  const response = await send(path, init)
  if (!response.ok) throw new ApiError(response.status, userMessage(response.status))
  return (await response.json()) as T
}

async function refreshOnce(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight
  const performRefresh = async (): Promise<boolean> => {
    const csrf = readStoredCsrf()
    if (!csrf) {
      notifySessionExpired()
      return false
    }
    try {
      const payload = await jsonRequest<TokenResponse>("/api/v1/auth/refresh", {
        method: "POST",
        headers: { [csrfHeaderName]: csrf },
      })
      saveTokens(payload)
      return true
    } catch {
      notifySessionExpired()
      return false
    }
  }
  const lockManager = typeof navigator !== "undefined" ? navigator.locks : undefined
  const refresh = lockManager
    ? lockManager.request("roomchat-auth-refresh", { mode: "exclusive" }, performRefresh)
    : performRefresh()
  refreshInFlight = refresh.finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

export function restoreSession(): Promise<boolean> {
  if (restorationInFlight) return restorationInFlight
  restorationInFlight = refreshOnce().finally(() => {
    restorationInFlight = null
  })
  return restorationInFlight
}

export async function register(payload: RegisterPayload): Promise<RegisteredUser> {
  return jsonRequest<RegisteredUser>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  })
}

export async function login(payload: LoginPayload): Promise<void> {
  const tokens = await jsonRequest<TokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  })
  saveTokens(tokens)
}

export async function authenticatedRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const sendWithAccessToken = async (): Promise<Response> => {
    const token = accessToken
    if (!token) throw new ApiError(401, userMessage(401))
    const headers = new Headers(init.headers)
    headers.set("Authorization", `Bearer ${token}`)
    const method = (init.method || "GET").toUpperCase()
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
      const csrf = readStoredCsrf()
      if (csrf) headers.set(csrfHeaderName, csrf)
    }
    return send(path, { ...init, headers })
  }

  let response = await sendWithAccessToken()
  if (response.status === 401) {
    const refreshed = await refreshOnce()
    if (!refreshed) throw new ApiError(401, userMessage(401))
    response = await sendWithAccessToken()
    if (response.status === 401) notifySessionExpired()
  }
  if (!response.ok) throw new ApiError(response.status, userMessage(response.status))
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function logout(): Promise<void> {
  const csrf = readStoredCsrf()
  if (!csrf) throw new ApiError(403, userMessage(403))
  const response = await send("/api/v1/auth/logout", {
    method: "POST",
    headers: { [csrfHeaderName]: csrf },
  })
  if (!response.ok) throw new ApiError(response.status, userMessage(response.status))
}

export async function logoutAll(): Promise<void> {
  const csrf = readStoredCsrf()
  if (!csrf) throw new ApiError(403, userMessage(403))
  await authenticatedRequest<void>("/api/v1/auth/logout-all", {
    method: "POST",
    headers: { [csrfHeaderName]: csrf },
  })
}

export async function checkServiceHealth(): Promise<boolean> {
  try {
    const response = await send("/api/v1/health", { method: "GET" })
    return response.ok
  } catch {
    return false
  }
}

