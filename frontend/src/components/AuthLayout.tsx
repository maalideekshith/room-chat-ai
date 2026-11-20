import type { ReactNode } from "react"
import { BrandMark } from "./Brand"
import { Icon } from "./Icon"
import { ApiStatus } from "./ApiStatus"

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <main className="auth-layout">
      <aside className="auth-story" aria-label="About Room Chat AI">
        <BrandMark />
        <div className="auth-story__body">
          <p className="eyebrow eyebrow--light">A clearer way to work together</p>
          <h1>Good thinking happens <span>in the room.</span></h1>
          <p className="auth-story__copy">
            Bring conversations and shared context into one calm, collaborative space.
          </p>
          <div className="story-note">
            <span className="story-note__icon"><Icon name="shield" /></span>
            <span><strong>Designed for clarity</strong><small>Keep the conversation close to the work.</small></span>
          </div>
        </div>
        <p className="auth-story__footer">ROOM CHAT AI <span>·</span> WORK, WITH CONTEXT</p>
        <div className="auth-story__texture" aria-hidden="true" />
      </aside>
      <section className="auth-panel">
        <div className="auth-panel__mobile-brand"><BrandMark /></div>
        <div className="auth-panel__content">{children}</div>
        <div className="auth-panel__footer"><ApiStatus /><span>ROOM CHAT AI <i>·</i> ACCOUNT ACCESS</span></div>
      </section>
    </main>
  )
}
