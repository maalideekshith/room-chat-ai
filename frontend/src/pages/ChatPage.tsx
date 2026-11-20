import { Icon } from "../components/Icon"

export default function ChatPage() {
  return (
    <main className="section-page">
      <header className="section-page__heading">
        <p className="overview-eyebrow">PRIVATE MESSAGING</p>
        <h1>Chat</h1>
        <p>One-to-one conversations with people in your Room Chat AI network.</p>
      </header>
      <section className="section-empty" aria-labelledby="chat-unavailable">
        <span className="section-empty__icon"><Icon name="messages" /></span>
        <p className="overview-eyebrow">NOT AVAILABLE YET</p>
        <h2 id="chat-unavailable">Private chat is not available yet</h2>
        <p>User search, direct messages, attachments and notifications are not connected. Messages will not be sent or stored here.</p>
      </section>
    </main>
  )
}
