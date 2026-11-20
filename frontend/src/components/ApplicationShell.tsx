import { useState } from "react"
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"
import { BrandGlyph, BrandMark } from "./Brand"
import { Icon } from "./Icon"

const primaryNavigation = [
  { label: "Overview", to: "/app", icon: "home" },
  { label: "Room", to: "/app/room", icon: "brand" },
  { label: "Team Room", to: "/app/team-room", icon: "rooms" },
  { label: "Chat", to: "/app/chat", icon: "messages" },
] as const

function sectionTitle(pathname: string): string {
  if (pathname.startsWith("/app/room")) return "Room"
  if (pathname.startsWith("/app/team-room")) return "Team Room"
  if (pathname.startsWith("/app/chat")) return "Chat"
  if (pathname.startsWith("/app/settings")) return "Settings"
  return "Overview"
}

export default function ApplicationShell() {
  const { signOut, signOutAll } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const isOverview = location.pathname === "/app"
  const [mobileNavigationOpen, setMobileNavigationOpen] = useState(false)
  const [accountMenuOpen, setAccountMenuOpen] = useState(false)
  const [signingOut, setSigningOut] = useState(false)

  async function leave(allSessions: boolean) {
    setSigningOut(true)
    const confirmed = allSessions ? await signOutAll() : await signOut()
    navigate("/login", {
      replace: true,
      state: { notice: confirmed ? "You’re signed out." : "You’re signed out on this device." },
    })
  }

  function navigationItems() {
    return (
      <>
        <div className="sidebar__brand">
          <BrandMark compact />
        </div>
        <nav className="side-nav" aria-label="Primary navigation">
          {primaryNavigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/app"}
              className={({ isActive }) => `side-nav__item${isActive ? " is-active" : ""}`}
              onClick={() => setMobileNavigationOpen(false)}
            >
              {item.icon === "brand" ? <BrandGlyph className="room-nav-glyph" /> : <Icon name={item.icon} />}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar__bottom">
          <nav className="sidebar__settings" aria-label="Application settings">
            <NavLink
              to="/app/settings"
              className={({ isActive }) => `side-nav__item${isActive ? " is-active" : ""}`}
              onClick={() => setMobileNavigationOpen(false)}
            >
              <Icon name="settings" />
              <span>Settings</span>
            </NavLink>
          </nav>
        </div>
      </>
    )
  }

  return (
    <div className="app-shell">
      <aside className="sidebar sidebar--desktop">{navigationItems()}</aside>
      {mobileNavigationOpen && (
        <div className="mobile-nav-layer">
          <button
            className="mobile-nav-layer__scrim"
            type="button"
            aria-label="Close application navigation"
            onClick={() => setMobileNavigationOpen(false)}
          />
          <aside className="sidebar sidebar--mobile" aria-label="Application navigation">
            <button
              className="mobile-nav-close"
              type="button"
              aria-label="Close application navigation"
              onClick={() => setMobileNavigationOpen(false)}
            >
              <Icon name="close" />
            </button>
            {navigationItems()}
          </aside>
        </div>
      )}
      <div className="app-main">
        <header className={`app-topbar${isOverview ? " app-topbar--overview" : ""}`}>
          {!isOverview && <>
            <button
              className="icon-button mobile-menu-button"
              type="button"
              aria-label="Open application navigation"
              onClick={() => setMobileNavigationOpen(true)}
            >
              <Icon name="menu" />
            </button>
            <div className="topbar-crumb">
              <span>Room Chat AI</span>
              <Icon name="chevron" />
              <strong>{sectionTitle(location.pathname)}</strong>
            </div>
          </>}
          <div className="topbar-actions">
            <div className="account-menu-wrap">
              <button
                className="account-trigger"
                type="button"
                aria-expanded={accountMenuOpen}
                aria-haspopup="menu"
                aria-label="My account"
                disabled={signingOut}
                onClick={() => setAccountMenuOpen((open) => !open)}
              >
                <span className="avatar"><Icon name="user" /></span>
                  <span className="account-trigger__label"><strong>My account</strong></span>
                <Icon name="chevron" />
              </button>
              {accountMenuOpen && (
                <div className="account-menu" role="menu">
                  <p className="account-menu__heading">Session controls</p>
                  <button type="button" role="menuitem" onClick={() => void leave(false)}>
                    <Icon name="logout" /> Sign out
                  </button>
                  <button type="button" role="menuitem" onClick={() => void leave(true)}>
                    <Icon name="shield" /> Sign out all sessions
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>
        {isOverview && <nav className="overview-mobile-nav" aria-label="Mobile primary navigation">
          {primaryNavigation.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.to === "/app"} aria-label={item.label}>
              {item.icon === "brand" ? <BrandGlyph className="room-nav-glyph" /> : <Icon name={item.icon} />}
              <span>{item.label}</span>
            </NavLink>
          ))}
          <NavLink to="/app/settings" aria-label="Settings"><Icon name="settings" /><span>Settings</span></NavLink>
        </nav>}
        <Outlet />
      </div>
    </div>
  )
}
