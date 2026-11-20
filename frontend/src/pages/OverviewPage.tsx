import { Link } from "react-router-dom"
import { BrandGlyph } from "../components/Brand"
import { Icon } from "../components/Icon"

export default function OverviewPage() {
  return (
    <main className="overview-page">
      <section className="overview-welcome">
        <div className="overview-welcome__copy">
          <p className="overview-eyebrow">YOUR WORKSPACE</p>
          <h1>Welcome to <span>Room Chat AI</span></h1>
          <p>Choose a space to continue your work. Your personal Room is ready for private AI conversations and knowledge.</p>
          <Link className="overview-primary-link" to="/app/room">
            <BrandGlyph className="room-cta-glyph" />Open Room<Icon name="arrow" />
          </Link>
        </div>
      </section>

      <section className="overview-section" aria-labelledby="quick-access-heading">
        <div className="overview-section-heading">
          <div><p className="overview-eyebrow">WORKSPACES</p><h2 id="quick-access-heading">Go to a space</h2></div>
        </div>
        <div className="overview-space-grid">
          <Link className="overview-space-card" to="/app/room">
            <span className="overview-space-icon"><BrandGlyph className="room-card-glyph" /></span>
            <span className="overview-space-copy"><strong>Room</strong><small>Your private AI workspace, conversations and knowledge sources.</small></span>
            <Icon name="arrow" />
          </Link>
          <Link className="overview-space-card overview-space-card--unavailable" to="/app/team-room">
            <span className="overview-space-icon"><Icon name="rooms" /></span>
            <span className="overview-space-copy"><strong>Team Room</strong><small>Shared workspaces for teams. Collaboration APIs are not available yet.</small></span>
            <Icon name="arrow" />
          </Link>
          <Link className="overview-space-card overview-space-card--unavailable" to="/app/chat">
            <span className="overview-space-icon"><Icon name="messages" /></span>
            <span className="overview-space-copy"><strong>Chat</strong><small>Private one-to-one messaging. Messaging APIs are not available yet.</small></span>
            <Icon name="arrow" />
          </Link>
        </div>
      </section>
    </main>
  )
}
