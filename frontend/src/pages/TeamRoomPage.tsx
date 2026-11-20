import { Icon } from "../components/Icon"

export default function TeamRoomPage() {
  return (
    <main className="section-page">
      <header className="section-page__heading">
        <p className="overview-eyebrow">COLLABORATIVE WORKSPACE</p>
        <h1>Team Room</h1>
        <p>A shared space for your team’s conversations, members and project knowledge.</p>
      </header>
      <section className="section-empty" aria-labelledby="team-room-unavailable">
        <span className="section-empty__icon"><Icon name="rooms" /></span>
        <p className="overview-eyebrow">COMING LATER</p>
        <h2 id="team-room-unavailable">Team Rooms aren’t available yet</h2>
        <p>Room Chat AI does not have team workspace APIs yet. No room, membership or invitation has been created.</p>
      </section>
    </main>
  )
}
