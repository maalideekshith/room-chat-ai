# Room Chat AI - Product

## Vision

Room Chat AI is a SaaS workspace where individuals and small teams turn their own documents, links, and conversations into grounded AI answers, reports, and shared project memory.

## Status Legend

- **Implemented**: present in the repository and verified.
- **Planned**: agreed product direction, not built yet.
- **Decided**: founder-approved architecture default.

## Product Modules

### 1. SOLO

Personal AI workspace for one user.

Planned capabilities:
- One private personal workspace per user, using shared workspace infrastructure.
- Upload images, PDF, DOCX, TXT, and other supported documents.
- Submit website URLs as knowledge sources.
- Chat with AI grounded in the user's own sources.
- Generate summaries, analysis, and reports.
- Personal conversation and file history.
- Full BYOK: connect multiple providers, store multiple credentials, select provider, credential and model per conversation, and configure a default.
- Switch provider or model without losing conversation history.

### 2. TEAM

Shared rooms for project work.

Planned capabilities:
- Team rooms with a maximum of 10 active members including the owner.
- Invite members by email.
- Email and in-app notifications.
- Roles: Owner, Admin, Member.
- Members upload images, documents, and URLs.
- AI understands shared room documents, conversations, and activity.
- Project reports covering overview, completed work, changes, decisions, pending tasks, risks, and suggestions.
- Room activity history with source references.
- AI suggestions must never be presented as confirmed decisions.
- Ownership transfer is required before an owner leaves.

### 3. CHAT

Private one-to-one messaging.

Planned capabilities:
- Find registered users.
- Real-time direct messaging.
- Conversation history.
- File sharing and notifications.
- Direct conversations have exactly two participants.

### 4. User Identity

Decided:
- Every user receives a globally unique, immutable platform user ID (UUID).
- Usernames are unique.
- One identity spans Solo, Team, and Chat.
- Authentication uses short-lived JWT access tokens and rotating refresh tokens in Secure, HttpOnly cookies.
- Passwords are hashed with Argon2.

Implemented today:
- Nothing beyond scaffolding; no user accounts exist.

### 5. AI Providers

Decided:
- Bring Your Own Key (BYOK) for Solo and room AI.
- Initial providers: OpenAI, Anthropic Claude, Google Gemini.
- Multiple credentials per user and per provider.
- Provider-independent adapter layer.
- User selects provider, credential and model per conversation.
- User can set a default provider and model.
- Credentials are envelope-encrypted at rest.
- Credentials can be added, validated, replaced and revoked.
- Keys are never returned to the frontend, logs or other users after saving.

### 6. SaaS Business

Decided:
- Architecture supports usage tracking, subscription entitlements and billing later.
- Billing and pricing UI are explicitly out of scope for now.

## Implemented Today (Day 1)

- Documentation set.
- Vite + React + TypeScript + Tailwind frontend shell with a health indicator.
- FastAPI backend with `/health` and `/api/v1/health`.
- CORS for local frontend development.
- Basic pytest health tests.
- No authentication, database, chat, AI, RAG, Redis, or Celery.
