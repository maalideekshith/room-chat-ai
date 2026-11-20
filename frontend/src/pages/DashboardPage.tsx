import { useState } from "react"
import { NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "../auth/AuthContext"
import { BrandMark, BrandGlyph } from "../components/Brand"
import { Icon, type IconName } from "../components/Icon"

interface NavigationItem {
  label: string
  icon: IconName
  available: boolean
}

const navigation: NavigationItem[] = [
  { label: "Overview", icon: "home", available: true },
  { label: "Conversations", icon: "messages", available: false },
  { label: "Rooms", icon: "rooms", available: false },
  { label: "Shared knowledge", icon: "knowledge", available: false },
]

export default function DashboardPage() {
  const { signOut, signOutAll } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [working, setWorking] = useState(false)

  async function leave(revokeAll: boolean) {
    setWorking(true)
    const confirmed = revokeAll ? await signOutAll() : await signOut()
    navigate("/login", {
      replace: true,
      state: {
        notice: confirmed
          ? "You’re signed out."
          : "You’re signed out on this device. We couldn’t reach the server to close the session.",
      },
    })
  }

  const navContent = (
    <>
      <div className="sidebar__brand"><BrandMark compact /></div>
      <div className="sidebar__section-label">YOUR SPACE</div>
      <nav className="side-nav" aria-label="Main navigation">
        {navigation.map((item) => item.available ? (
          <NavLink
            key={item.label}
            to="/app"
            end
            className={({ isActive }) => `side-nav__item${isActive ? " is-active" : ""}`}
            onClick={() => setMobileNavOpen(false)}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </NavLink>
        ) : (
          <div className="side-nav__item side-nav__item--disabled" key={item.label} aria-disabled="true">
            <Icon name={item.icon} />
            <span>{item.label}</span>
            <span className="side-nav__soon">Soon</span>
          </div>
        ))}
      </nav>
      <div className="sidebar__bottom">
        <div className="sidebar__session"><span className="status-dot" /> Secure session</div>
        <p>Room Chat AI<br /><span>Work, with context.</span></p>
      </div>
    </>
  )

  return (
    <div className="app-shell">
      <aside className="sidebar sidebar--desktop">{navContent}</aside>
      {mobileNavOpen && (
        <div className="mobile-nav-layer">
          <button className="mobile-nav-layer__scrim" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />
          <aside className="sidebar sidebar--mobile">
            <button className="mobile-nav-close" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)}><Icon name="close" /></button>
            {navContent}
          </aside>
        </div>
      )}

      <div className="app-main">
        <header className="app-topbar">
          <button
            className="icon-button mobile-menu-button"
            type="button"
            aria-label="Open navigation"
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen(true)}
          >
            <Icon name="menu" />
          </button>
          <div className="topbar-crumb"><span>Room Chat AI</span><Icon name="chevron" /><strong>Overview</strong></div>
          <div className="topbar-actions">
            <div className="account-menu-wrap">
              <button
                className="account-trigger"
                type="button"
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                onClick={() => setMenuOpen((open) => !open)}
                disabled={working}
              >
                <span className="avatar">M</span>
                <span className="account-trigger__label"><strong>My account</strong><small>Member</small></span>
                <Icon name="chevron" />
              </button>
              {menuOpen && (
                <div className="account-menu" role="menu">
                  <div className="account-menu__heading">Signed in to Room Chat AI</div>
                  <button role="menuitem" type="button" disabled={working} onClick={() => void leave(false)}>
                    <Icon name="logout" /> Sign out
                  </button>
                  <button role="menuitem" type="button" disabled={working} onClick={() => void leave(true)}>
                    <Icon name="shield" /> Sign out all sessions
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="dashboard-content">
          <div className="dashboard-kicker"><span className="status-dot" /> YOUR WORKSPACE</div>
          <section className="welcome-panel">
            <div className="welcome-panel__copy">
              <p className="eyebrow">A GOOD PLACE TO BEGIN</p>
              <h1>Make room for<br /><span>good thinking.</span></h1>
              <p className="welcome-panel__description">
                Your account is ready. Room Chat AI is built to bring conversations and shared context together as your workspace grows.
              </p>
            </div>
            <div className="welcome-panel__art" aria-hidden="true">
              <div className="orbit orbit--one" />
              <div className="orbit orbit--two" />
              <div className="orbit orbit--three" />
              <BrandGlyph className="welcome-panel__glyph" />
              <span className="art-node art-node--top" />
              <span className="art-node art-node--side" />
              <span className="art-node art-node--bottom" />
            </div>
            <div className="welcome-panel__foot"><span><Icon name="shield" /> Your session is active</span><span>Access controlled</span></div>
          </section>

          <section className="workspace-intro" aria-labelledby="workspace-intro-title">
            <div>
              <p className="eyebrow">BUILT AROUND THE WAY TEAMS THINK</p>
              <h2 id="workspace-intro-title">One place for work with context.</h2>
              <p>Room Chat AI is taking shape around the conversations, knowledge, and decisions teams build together.</p>
            </div>
            <span className="intro-mark" aria-hidden="true"><Icon name="spark" /></span>
          </section>

          <div className="capability-grid" aria-label="Room Chat AI workspace areas">
            <article className="capability-card">
              <span className="capability-card__icon"><Icon name="messages" /></span>
              <div><span className="capability-card__status">IN THE WORKS</span><h3>Conversations</h3><p>Keep the discussion close to the work it moves forward.</p></div>
            </article>
            <article className="capability-card">
              <span className="capability-card__icon"><Icon name="rooms" /></span>
              <div><span className="capability-card__status">IN THE WORKS</span><h3>Team rooms</h3><p>Give every project a shared place for people and context.</p></div>
            </article>
            <article className="capability-card">
              <span className="capability-card__icon"><Icon name="knowledge" /></span>
              <div><span className="capability-card__status">IN THE WORKS</span><h3>Shared knowledge</h3><p>Bring useful sources alongside the conversations they inform.</p></div>
            </article>
          </div>

          <footer className="dashboard-footer"><span>ROOM CHAT AI</span><span>Thoughtful collaboration starts with context.</span></footer>
        </main>
      </div>
    </div>
  )
}
