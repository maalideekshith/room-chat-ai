# Room Chat AI - 40-Day Development Plan

## Status

Day 1 complete. Day 2 not started. Founder-approved defaults from the architecture audit are reflected below.

## Phase 1 - Foundation (Days 1-6)

| Day | Focus |
|---|---|
| 1 | Docs, frontend/backend scaffolding, health endpoints, connection check. Completed. |
| 2 | Database foundation, local PostgreSQL/pgvector, Alembic baseline. |
| 3 | User identity, Argon2 passwords, JWT access tokens. |
| 4 | Refresh cookies, rotation, revocation, CSRF and protected routes. |
| 5 | Personal workspace creation and owner-only access. |
| 6 | Shared conversation/message schema and authorization primitives. |

## Phase 2 - Solo and Files (Days 7-13)

| Day | Focus |
|---|---|
| 7 | File storage abstraction (local/S3-compatible) and upload validation. |
| 8 | Source records, extraction/OCR pipeline foundation. |
| 9 | Chunking and configurable embedding providers with metadata. |
| 10 | pgvector retrieval scoped to Solo workspace. |
| 11 | Grounded Solo chat with citations. |
| 12 | BYOK credential vault, envelope encryption, validation and revocation. |
| 13 | Per-conversation provider/credential/model selection and defaults. |

## Phase 3 - Team (Days 14-22)

| Day | Focus |
|---|---|
| 14 | Team workspaces and rooms. |
| 15 | Memberships, roles, transactional 10-member capacity. |
| 16 | Email adapter, outbox, invitations and acceptance. |
| 17 | In-app and email notifications. |
| 18 | Room sources and shared knowledge ingestion. |
| 19 | Team conversations using shared messaging infrastructure. |
| 20 | Realtime delivery with WebSockets. |
| 21 | Activity history and provenance. |
| 22 | Team project reports and ownership transfer. |

## Phase 4 - Direct Chat (Days 23-27)

| Day | Focus |
|---|---|
| 23 | Direct conversations with exactly two participants. |
| 24 | User discovery and conversation creation. |
| 25 | Real-time direct messaging on shared message infrastructure. |
| 26 | File sharing and conversation history. |
| 27 | Direct chat notifications and presence basics. |

## Phase 5 - AI Hardening and Deletion (Days 28-33)

| Day | Focus |
|---|---|
| 28 | Provider-independent model catalog and fallback behavior. |
| 29 | Retrieval quality, citation accuracy and embedding versioning. |
| 30 | Re-embedding jobs and deletion of derived data. |
| 31 | Usage metering and cost tracking. |
| 32 | MCP integration foundation. |
| 33 | Authorization, isolation and credential security tests. |

## Phase 6 - SaaS and Launch (Days 34-40)

| Day | Focus |
|---|---|
| 34 | Subscription and entitlement data model. |
| 35 | Plan limit enforcement hooks. |
| 36 | Security review and key-handling audit. |
| 37 | Docker and deployment configuration. |
| 38 | End-to-end and performance testing. |
| 39 | Pricing UI and onboarding polish. |
| 40 | Launch readiness review. |

## Guardrails

- No microservices.
- No feature before its authorization model.
- No plaintext provider keys.
- No cross-room retrieval.
- No billing UI before core flows are stable.
- No global AI provider assumption.
- No retention of deleted user content.
