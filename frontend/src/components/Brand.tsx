import { Link } from "react-router-dom"

export function BrandMark({ compact = false }: { compact?: boolean }) {
  return (
    <Link className={`brand${compact ? " brand--compact" : ""}`} to="/" aria-label="Room Chat AI home">
      <span className="brand__mark" aria-hidden="true">
        <svg viewBox="0 0 40 40" fill="none">
          <path d="M8 9.5A4.5 4.5 0 0 1 12.5 5h16A4.5 4.5 0 0 1 33 9.5v12a4.5 4.5 0 0 1-4.5 4.5H19l-7.2 5.5v-5.5h-.3A4.5 4.5 0 0 1 7 21.5v-12A4.5 4.5 0 0 1 8 9.5Z" />
          <path d="M14 13h12M14 18h8" />
        </svg>
      </span>
      <span className="brand__wordmark">Room<span>Chat</span><i>AI</i></span>
    </Link>
  )
}

export function BrandGlyph({ className = "" }: { className?: string }) {
  return (
    <span className={`brand-glyph ${className}`} aria-hidden="true">
      <svg viewBox="0 0 40 40" fill="none">
        <path d="M8 9.5A4.5 4.5 0 0 1 12.5 5h16A4.5 4.5 0 0 1 33 9.5v12a4.5 4.5 0 0 1-4.5 4.5H19l-7.2 5.5v-5.5h-.3A4.5 4.5 0 0 1 7 21.5v-12A4.5 4.5 0 0 1 8 9.5Z" />
        <path d="M14 13h12M14 18h8" />
      </svg>
    </span>
  )
}
