# Room Chat AI - Architecture

## Status

Day 1 implemented scaffolding and health endpoints. Day 2 added the async database foundation. Business features below remain target architecture.

## Style

Modular monolith. One FastAPI deployable and one React SPA. One PostgreSQL database with pgvector. Redis, WebSockets, Celery and MCP are planned additions.

## Database Infrastructure

Implemented in Day 2:
- Async SQLAlchemy 2 engine with `asyncpg` and connection pooling.
- Single Pydantic Settings source for environment configuration.
- `Base` and centralized model registration package for future models.
- FastAPI session dependency with rollback and cleanup.
- Alembic async migrations driven by the same settings.
- Separate liveness and database readiness endpoints.
- pgvector extension migration that fails clearly when the server extension is absent.

Connection failures are handled at the readiness boundary and return no credentials or SQL details.

## Responsibilities

### Frontend

- Authentication screens and session handling.
- Solo workspace, team rooms and direct chat UI.
- Source upload/progress, citations, reports, notifications.
- AI provider and model selection UI.
- Calls REST API and, later, WebSocket channels.
- Never receives provider keys or cross-room data.

### Backend

- Identity, authentication, authorization and tenant isolation.
- Shared conversations, messages, rooms, memberships, invitations.
- File storage abstraction and source ingestion.
- RAG retrieval, AI provider adapters, report generation.
- Activity history, provenance, usage metering.
- Future billing hooks.

## Backend Modules

- `core`: settings, database, security, encryption, storage/email abstractions.
- `identity`: users, JWT access tokens, refresh sessions, platform IDs.
- `solo`: personal workspace lifecycle (shared workspace infrastructure).
- `team`: team rooms, memberships, invitations, roles, capacity.
- `messaging`: shared conversations and messages for direct and team.
- `files`: upload validation, storage adapters, source records.
- `rag`: ingest, extract/OCR, chunk, embed, retrieve.
- `ai`: provider adapters, BYOK credential vault, model catalog.
- `reports`: generated reports with provenance.
- `notifications`: in-app notifications and email outbox.
- `activity`: room activity event log.
- `billing`: future usage, entitlements, subscriptions.

## Authentication and Sessions

Decided:
- Short-lived JWT access tokens (target 15 minutes).
- Refresh tokens stored in Secure, HttpOnly cookies, path-scoped to the refresh endpoint.
- Refresh-token rotation on every use.
- Token families with reuse detection; reuse revokes the family.
- Server-side refresh session records allow revocation and logout-all.
- Argon2id password hashing with per-password salt.
- CSRF protection required for cookie-authenticated state-changing requests (SameSite plus double-submit token).
- Access tokens are never stored in localStorage.

Constraints:
- No refresh token in response bodies.
- Password reset and email verification are separate future flows.
- Production must rate-limit login, refresh and registration through a shared gateway or limiter; no reliable shared limiter is implemented in the application yet.

## Tenancy Model

Decided:
- A `workspace` is the tenant boundary.
- Every user receives exactly one personal workspace on registration.
- Personal workspace access is restricted to its owner.
- Team workspaces contain team rooms.
- Solo and Team share workspace infrastructure but remain logically separated in modules and APIs.
- Every room-scoped row carries `workspace_id` and/or `room_id`.
- Authorization occurs in a dependency/service layer before any query.
- Repository helpers require an explicit workspace or room scope; unscoped queries are prohibited except for controlled admin jobs.
- Cross-room and cross-workspace access fail closed.

## Messaging Model

Decided:
- Single shared `conversations` and `messages` infrastructure.
- Conversation types: `direct` and `team`.
- Direct conversations have exactly two participants.
- Team conversations follow room membership and role permissions.
- One delivery/history implementation serves both types.
- WebSocket channels resolve conversation authorization at connect time and re-check on reconnect.

## Room Membership and Capacity

Decided:
- Maximum 10 active members including the owner.
- Capacity is enforced transactionally on the backend using room-level locking.
- Pending invitations count against capacity reservation when created.
- Accepting an invitation re-checks capacity inside the transaction.
- Leaving a room frees a slot.
- Ownership transfer must complete before an owner can leave.
- Admin cannot remove the owner; owner transfer is explicit.

## File Storage

Decided:
- Storage abstraction with local filesystem for development and S3-compatible object storage for production.
- Private buckets/prefixes; no direct storage paths returned to clients.
- Access through short-lived signed URLs or authenticated backend streaming.
- Validate MIME type, extension, size and room permissions on upload.
- Store checksum and immutable source metadata.
- Deletion removes derived chunks, embeddings and file objects subject to retention rules.

## Email

Decided:
- Provider-independent email adapter.
- Transactional outbox pattern for reliable sending.
- Supports invitations and notifications.
- Business logic never depends on a specific email vendor.
- Local development uses a console/file adapter.

## AI Provider Integration (BYOK)

Decided:
- Users may connect multiple credentials across OpenAI, Anthropic Claude and Google Gemini.
- Multiple credentials per provider are allowed.
- Each conversation can select provider, credential and model.
- Users can set a default provider and model.
- Credential lifecycle: add, validate, replace, revoke.
- Envelope encryption: data key encrypts credentials; master key from environment/secret manager.
- Key metadata stored: provider, label, suffix, status, timestamps.
- Plaintext keys exist only in server memory for the owning user's request.
- Keys never appear in API responses, logs, traces, errors or analytics.
- Switching provider/model preserves conversation history.
- Backend resolves provider, credential and model per AI request; there is no global application provider.

## Source Provenance

- Answers and reports store source references.
- Sources are immutable snapshots with checksum and ingestion status.
- Reports label AI suggestions separately from confirmed decisions.
- Activity events record actor, action, target and timestamp.

## Data Retention and Deletion

Decided:
- Users can delete conversations, messages and uploaded content.
- Deleting a conversation or source purges messages, chunks and embeddings derived from it.
- Derived AI runs retain non-content metadata where needed for usage/audit, not deleted content.
- Security and audit records follow a separate, documented retention policy.
- Deleted user content is not retained indefinitely and is not silently resurrected by re-embedding jobs.

## SaaS Readiness

- Usage events and entitlements are planned in the schema.
- Billing integration and pricing UI are not implemented.
- Plan limits must be enforceable through entitlement checks, not hard-coded UI.

## Planned Runtime Additions

- Redis: caching, rate limits, notification fan-out.
- WebSockets: team and direct delivery.
- Celery: ingestion, embeddings, reports, email.
- MCP: controlled tool access with explicit authorization.

## Implemented Solo boundary

- `/api/v1/solo` endpoints use the shared authenticated-user dependency and scope database reads/writes by `user_id`.
- A user has one `solo_workspaces` row. Conversations, messages, sources and vector chunks carry owner scope, reinforced by composite foreign keys.
- AI provider adapters are server-side and provider independent. Each user credential is envelope-encrypted with a deployment-provided master key.
- Source storage uses a `FileStorage` protocol with a private local implementation. Production object storage can implement the same boundary.
- Source extraction, embedding and retrieval currently run synchronously; queueing, retries and production storage are deployment follow-ups.

## Non-Goals

- Microservices.
- Cross-tenant data sharing.
- Frontend-side AI keys.
- Billing implementation now.
