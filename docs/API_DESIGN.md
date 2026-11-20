# Room Chat AI - API Design

## Status

Implemented: liveness and database readiness endpoints, registration, login, refresh, logout and logout-all. Resource APIs and `/me` remain planned.

`/health` and `/api/v1/health` are liveness checks. `/api/v1/health/db` executes `SELECT 1` and returns 200 when the database is reachable or 503 with `{"status":"unavailable","database":"unavailable"}` when it is not. No SQL or credentials are returned.

## Conventions

- Base path: `/api/v1`.
- JSON request/response bodies.
- Short-lived JWT access token in the `Authorization: Bearer` header.
- Refresh token only in a Secure, HttpOnly cookie.
- CSRF token required for cookie-authenticated state-changing requests.
- Cursor pagination for history endpoints.
- Server-generated IDs and timestamps.
- Never return provider keys, password hashes, storage paths or refresh tokens.

## Authentication

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/logout-all`
- `GET /me`

Rules:
- Access token lifetime: short (target 15 minutes).
- Refresh rotation on every use; reuse revokes the token family.
- Refresh cookie: Secure, HttpOnly, SameSite, narrow path.
- Login and refresh return a CSRF token alongside the access token. Refresh and logout requests require that value to match the `csrf_token` cookie and `X-CSRF-Token` header.
- Access-token JWT algorithm is fixed to HS256 by application configuration.

## Solo

- `GET /solo/workspace`
- `GET /solo/conversations`
- `POST /solo/conversations`
- `GET /solo/conversations/{conversation_id}/messages`
- `POST /solo/conversations/{conversation_id}/messages`
- `PUT /solo/conversations/{conversation_id}/ai-settings`
- `POST /solo/sources/files`
- `POST /solo/sources/urls`
- `POST /solo/conversations/{conversation_id}/reports`
- `DELETE /solo/conversations/{conversation_id}`
- `DELETE /solo/sources/{source_id}`

Solo access is owner-only.

## Team Rooms

- `POST /rooms`
- `GET /rooms`
- `GET /rooms/{room_id}`
- `PATCH /rooms/{room_id}`
- `DELETE /rooms/{room_id}`
- `GET /rooms/{room_id}/members`
- `PATCH /rooms/{room_id}/members/{user_id}`
- `DELETE /rooms/{room_id}/members/{user_id}` (leave)
- `POST /rooms/{room_id}/ownership-transfer`
- `GET /rooms/{room_id}/invitations`
- `POST /rooms/{room_id}/invitations`
- `DELETE /rooms/{room_id}/invitations/{invitation_id}`
- `POST /invitations/{token}/accept`
- `POST /rooms/{room_id}/sources/files`
- `POST /rooms/{room_id}/sources/urls`
- `GET /rooms/{room_id}/activity`
- `POST /rooms/{room_id}/reports`
- `POST /rooms/{room_id}/conversations`
- `GET /rooms/{room_id}/conversations`

Capacity:
- Maximum 10 active members including owner.
- Invite and accept endpoints enforce capacity transactionally.
- Owner transfer is required before the owner can leave.

## Direct Chat

- `GET /chat/users` (discovery)
- `GET /chat/conversations`
- `POST /chat/conversations` (exactly two participants)
- `GET /chat/conversations/{conversation_id}/messages`
- `POST /chat/conversations/{conversation_id}/messages`
- WebSocket: `/ws/chat/{conversation_id}`

## AI Providers and Credentials

- `GET /ai/providers`
- `GET /ai/providers/{provider}/models`
- `GET /ai/credentials`
- `POST /ai/credentials`
- `PATCH /ai/credentials/{credential_id}`
- `POST /ai/credentials/{credential_id}/validate`
- `DELETE /ai/credentials/{credential_id}`
- `GET /ai/preferences`
- `PUT /ai/preferences`

Rules:
- Multiple credentials per provider are allowed.
- Responses expose only credential ID, provider, label, key suffix, status and validation time.
- Keys are accepted on create/replace and never returned.
- Revocation is immediate for new requests.
- Default provider/model is user-scoped.

## Notifications

- `GET /notifications`
- `POST /notifications/{id}/read`
- `POST /notifications/read-all`

## Authorization Rules

- Personal workspace routes require ownership.
- Team room routes require active membership.
- Owner/Admin-only routes are explicitly marked.
- Direct conversations require participation and exactly two participants.
- Source, report and activity reads are scope-checked.
- AI credential routes are user-scoped.
- Cross-tenant access returns 404 where appropriate to avoid enumeration.

## Error and Security Rules

- Stable error codes planned.
- Production must enforce login and refresh rate limits through a shared gateway or limiter before public exposure. No reliable shared limiter is implemented in the application yet.
- Rate limits are also required for registration, invitations, uploads and AI calls.
- No internal storage paths in responses.
- Signed URLs or authenticated streaming for file access.
- Request logs must redact credentials, cookies and tokens.

## Open API Decisions

- Invitation acceptance and email verification flow.
- Exact CSRF header convention.
- Signed URL lifetime and download policy.
- Whether room AI uses the invoking member's credential or a separate room credential.
