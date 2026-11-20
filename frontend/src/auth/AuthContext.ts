import { createContext, useContext } from "react"
import type { LoginPayload } from "../api/auth"

export type AuthStatus = "initializing" | "authenticated" | "unauthenticated"

interface AuthContextValue {
  status: AuthStatus
  notice: string | null
  signIn(payload: LoginPayload): Promise<void>
  signOut(): Promise<boolean>
  signOutAll(): Promise<boolean>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error("useAuth must be used inside AuthProvider")
  return value
}
