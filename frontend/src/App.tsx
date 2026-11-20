import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom"
import type { ReactNode } from "react"
import { useAuth } from "./auth/AuthContext"
import { AuthProvider } from "./auth/AuthProvider"
import ApplicationShell from "./components/ApplicationShell"
import ChatPage from "./pages/ChatPage"
import DashboardPage from "./pages/DashboardPage"
import LoginPage from "./pages/LoginPage"
import OverviewPage from "./pages/OverviewPage"
import RegisterPage from "./pages/RegisterPage"
import SettingsPage from "./pages/SettingsPage"
import TeamRoomPage from "./pages/TeamRoomPage"

function InitializingScreen() {
  return (
    <main className="initializing-screen" role="status" aria-live="polite">
      <span className="spinner spinner--large" aria-hidden="true" />
      <span>Restoring your secure session…</span>
    </main>
  )
}

function RootRedirect() {
  const { status } = useAuth()
  if (status === "initializing") return <InitializingScreen />
  return <Navigate to={status === "authenticated" ? "/app" : "/login"} replace />
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()
  if (status === "initializing") return <InitializingScreen />
  if (status === "unauthenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />
  }
  return children
}

function PublicRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === "initializing") return <InitializingScreen />
  if (status === "authenticated") return <Navigate to="/app" replace />
  return children
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
      <Route path="/app" element={<ProtectedRoute><ApplicationShell /></ProtectedRoute>}>
        <Route index element={<OverviewPage />} />
        <Route path="team-room" element={<TeamRoomPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/app" replace />} />
      </Route>
      <Route path="/app/room" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider><AppRoutes /></AuthProvider>
    </BrowserRouter>
  )
}
