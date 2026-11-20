import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react"
import * as authApi from "../api/auth"
import type { LoginPayload } from "../api/auth"
import { AuthContext, type AuthStatus } from "./AuthContext"

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("initializing")
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const handleExpired = () => setStatus("unauthenticated")
    window.addEventListener("roomchat:auth-expired", handleExpired)
    void authApi.restoreSession().then((restored) => {
      if (mounted) setStatus(restored ? "authenticated" : "unauthenticated")
    })
    return () => {
      mounted = false
      window.removeEventListener("roomchat:auth-expired", handleExpired)
    }
  }, [])

  const signIn = useCallback(async (payload: LoginPayload) => {
    await authApi.login(payload)
    setNotice(null)
    setStatus("authenticated")
  }, [])

  const signOut = useCallback(async () => {
    let confirmed = false
    try {
      await authApi.logout()
      confirmed = true
    } catch {
      confirmed = false
    } finally {
      authApi.clearLocalSession()
      setNotice(confirmed
        ? "You’re signed out."
        : "You’re signed out on this device. We couldn’t reach the server to close the session.")
      setStatus("unauthenticated")
    }
    return confirmed
  }, [])

  const signOutAll = useCallback(async () => {
    let confirmed = false
    try {
      await authApi.logoutAll()
      confirmed = true
    } catch {
      confirmed = false
    } finally {
      authApi.clearLocalSession()
      setNotice(confirmed
        ? "All sessions are signed out."
        : "You’re signed out on this device. We couldn’t reach the server to close other sessions.")
      setStatus("unauthenticated")
    }
    return confirmed
  }, [])

  const value = useMemo(
    () => ({ status, notice, signIn, signOut, signOutAll }),
    [status, notice, signIn, signOut, signOutAll],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
