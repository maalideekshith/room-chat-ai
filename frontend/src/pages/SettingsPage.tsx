import { Link } from "react-router-dom"
import { Icon } from "../components/Icon"

export default function SettingsPage() {
  return (
    <main className="section-page settings-page">
      <header className="section-page__heading">
        <p className="overview-eyebrow">PREFERENCES</p>
        <h1>Settings</h1>
        <p>Manage your AI providers and secure session controls.</p>
      </header>
      <section className="settings-card">
        <span className="overview-space-icon"><Icon name="key" /></span>
        <div><h2>AI providers</h2><p>Connect, update or remove your own provider credentials and choose a default model.</p></div>
        <Link to="/app/room" state={{ workspaceView: "providers" }}>Manage providers <Icon name="arrow" /></Link>
      </section>
      <section className="settings-card settings-card--quiet">
        <span className="overview-space-icon"><Icon name="shield" /></span>
        <div><h2>Account and security</h2><p>Use the account menu in the top bar to sign out on this device or revoke all sessions.</p></div>
      </section>
      <p className="settings-note">Account profile editing and preference APIs are not available yet.</p>
    </main>
  )
}
