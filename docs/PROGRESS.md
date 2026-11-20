# Room Chat AI - Progress

## Completed

### Day 1

- Documentation set created.
- React + TypeScript + Vite + Tailwind frontend scaffolded.
- FastAPI backend scaffolded.
- `GET /health` and `GET /api/v1/health` implemented.
- Local CORS configured.
- Frontend health-check integration implemented.
- Backend pytest health tests passing.
- Frontend production build passing.
- Python 3.13 virtual environment installed with FastAPI, Uvicorn, Pydantic Settings, pytest and httpx.

### Day 2

Database foundation:
- PostgreSQL 18.7 running through Docker.
- pgvector 0.8.7 installed.
- Alembic revision `20261118_0001` successfully applied to the main database and test database.

Backend:
- SQLAlchemy 2 async engine and session management with pooling, pre-ping and timeouts.
- FastAPI database dependency with rollback and cleanup.
- Database readiness endpoint `/api/v1/health/db`; liveness endpoints unchanged.
- Centralized database configuration through Pydantic Settings.
- Declarative Base and centralized model registration package.
- Alembic async migration configuration using the same settings and metadata.
- Initial pgvector extension migration with a clear failure when unavailable.

Testing:
- Test database isolation implemented; tests use `TEST_DATABASE_URL` and cannot fall back to the development database.
- Development database protection verified.
- 18 passed, 1 non-blocking deprecation warning with `TEST_DATABASE_URL` configured.
- 11 passed, 7 skipped without `TEST_DATABASE_URL`.
- `alembic current`: `20261118_0001 (head)`.
- `alembic check`: No new upgrade operations detected.
- Future write tests should add transaction rollback fixtures for per-test cleanup.

### Day 3

User identity and registration:
- `users` model with immutable UUID, canonical lowercase unique username/email, Argon2id password hash, active status, verification/login timestamps and audit timestamps.
- Database checks enforce lowercase values and 3-30 character usernames.
- Argon2id configuration: `time_cost=3`, `memory_cost=65536` KiB, `parallelism=4`, `hash_len=32`, `salt_len=16`.
- Registration endpoint `POST /api/v1/auth/register` with 201, 409 and 422 handling.
- Duplicate registration protection through database unique constraints and `IntegrityError` handling.
- Password and hash excluded from API responses and model representation.
- Alembic revision `20261119_0002_create_users.py` applied to main and test databases.
- Transaction-rollback fixture added so database write tests leave no persisted rows.

Day 3 verification:
- Backend tests: 53 passed, 1 non-blocking deprecation warning.
- Test database users table count after the suite: 0.
- `alembic current`: `20261119_0002 (head)`.
- `alembic check`: No new upgrade operations detected.
- True concurrent registration is not exercised by automated tests; database unique constraints and `IntegrityError` handling cover the race condition.

### Day 4

- Added username/email login with generic failures, inactive-account rejection, Argon2 verification in a worker thread, and `last_login_at` update.
- Added HS256 JWT access tokens with issuer, audience, expiry, issued-at, UUID subject and unique JWT ID validation.
- Added rotating refresh sessions with hashed opaque tokens, row locking, family replay revocation, logout and logout-all.
- Added Secure-configurable HttpOnly refresh cookies and double-submit CSRF validation for refresh/logout operations.
- Added reusable bearer current-user dependency and refresh-session migration `20261120_0003`.
- The migration could not be applied in this environment because the configured local PostgreSQL login failed; database-backed tests remain unverified here.
- Verification in this environment: 22 passed, 49 skipped, 2 warnings. Skips are PostgreSQL-backed tests because `TEST_DATABASE_URL` is unset.
- Offline SQL rendering for `20261120_0003` succeeded. The live migration remains unapplied here.

### Verification Snapshot

- PostgreSQL 18.7 via Docker; pgvector 0.8.7 in the prior Day 3 verification environment.
- Prior main and test database snapshot at revision `20261119_0002`; Day 4 revision `20261120_0003` is not confirmed applied.
- Backend: 53 passed with test database configured.
- Frontend production build: passed separately.

### Architecture decisions (documentation only)

- JWT access tokens with rotating refresh cookies, revocation and Argon2.
- One personal workspace per user on shared workspace infrastructure.
- Shared conversations/messages for direct and team types.
- Storage abstraction with local development and S3-compatible production.
- Provider-independent email adapter with outbox.
- Configurable embeddings/OCR with version metadata and re-embedding plan.
- Multiple encrypted AI credentials per user, per-conversation provider selection and defaults.
- Defined deletion behavior for content and derived data.
- Transactional room capacity of 10 including owner, with ownership transfer.
- Subscription and usage readiness documented, billing not implemented.

## Not Implemented

- Password reset and email verification flows.
- Team rooms, memberships, invitations, roles.
- Notifications and email delivery.
- Direct chat and WebSockets.
- Reports, MCP, Redis, Celery, billing and subscriptions.
- S3-compatible object storage and production deployment configuration.

## Manual Setup Required

- Keep the Docker PostgreSQL container running for database integration tests.
- Set `DATABASE_URL` and `TEST_DATABASE_URL` in `backend/.env` for local development and testing.
- Apply revision `20261120_0003` to development and test databases after correcting their local PostgreSQL credentials.

## Next

### Day 6 — Solo workspace

- Added a user-owned Solo workspace provisioned in the registration transaction and backfilled existing users by Alembic revision `20261121_0004`.
- Added conversation CRUD, scoped message history, per-conversation provider/model selection, user defaults and AI request handling. A user message is committed before provider work so provider failures do not discard the question.
- Added OpenAI, Anthropic and Gemini HTTP adapters behind provider-neutral chat/embedding protocols. Provider model choices are loaded from the user's own validated credential. Provider keys use AES-GCM envelope encryption and are never returned by credential schemas; the 32-byte master key is configured outside the repository.
- Added PDF, UTF-8 text and Markdown upload ingestion plus URL ingestion, size/type checks, DNS public-address checks, content extraction, overlapping chunks and pgvector embeddings. Sources record `processing`, `ready` or `failed`; ingestion errors do not appear as ready. A private local filesystem adapter implements the storage boundary.
- Added responsive Solo dashboard interactions for conversation history/search, message composition, provider credentials/defaults, model selection, file/URL sources, deletion, loading/error feedback and mobile sidebar behavior.
- Added focused backend service/security/provider and frontend workflow tests. Database-backed backend tests require `TEST_DATABASE_URL` and will be reported separately when unavailable.
- Production deployment must provide a managed/shared rate limiter for login, refresh, uploads and AI calls; this implementation does not add an in-process limiter.

Day 6 verification:

- Backend: `cd backend && .\.venv\Scripts\python.exe -m pytest -q` — 43 passed, 58 skipped, 2 warnings. Database integration tests were skipped because `TEST_DATABASE_URL` is unset.
- Migration: `cd backend && .\.venv\Scripts\alembic.exe upgrade head --sql` — passed and rendered revisions through `20261121_0004`; it was not applied to a database.
- `alembic check` — unable to run because the configured local PostgreSQL credentials fail with `password authentication failed for user "DELL"`.
- Backend dependency check: `.\.venv\Scripts\python.exe -m pip check` — no broken requirements.
- Frontend: `cd frontend && npm.cmd test -- --reporter=dot` — 3 test files and 23 tests passed; `npm.cmd run lint` passed; `npm.cmd run build` passed TypeScript project checks and Vite production build (37 modules transformed).
- Repository: `git diff --check` passed (Git emitted only LF-to-CRLF working-copy notices).
- No live provider calls or browser-based desktop/mobile visual verification were run.

Known limitations:

- The new migration has only been rendered as offline SQL so far; it has not been applied to a development or test database in this environment.
- Knowledge ingestion runs synchronously in the request and local filesystem storage is for development. Production needs S3-compatible storage, a durable job queue, retry/cleanup policies and operational limits.
- URL ingestion rejects non-public resolved addresses and redirects, but DNS is resolved once for validation and again by the HTTP client. Production should use a network egress proxy or an HTTP transport that pins validated addresses to close DNS-rebinding/TOCTOU exposure.
- Embedding is currently supported through the user's OpenAI or Gemini credential with a fixed 768-dimensional versioned vector. Scanned PDFs/OCR and model migration/re-embedding jobs are not implemented.
- No live provider credentials were available, so external provider calls were verified with adapter tests, not real accounts.
- No browser automation was available for visual review; responsive styles and workflow tests were inspected, but desktop/mobile rendering still needs manual review.

### Day 5 — Frontend authentication and design foundation

- Added responsive `/login`, `/register` and protected `/app` routes with reusable visual tokens, branded form components, responsive navigation and an initial workspace dashboard.
- Registration and login use the existing backend contracts. Registration does not imply login; the API has no full-name field, so the UI does not collect one.
- Added a centralized typed API client and authentication provider with `initializing`, `authenticated` and `unauthenticated` states. Protected routes wait for session restoration, and public auth routes redirect signed-in users to `/app`.
- Access JWTs remain in module memory only. The opaque refresh token remains in the backend-set HttpOnly cookie. The CSRF value is retained for refresh/logout calls; no access or refresh token is stored in browser storage. Requests use `credentials: include`.
- Startup restoration and protected-request 401 handling use refresh rotation. Refresh attempts are single-flight in a tab and use the browser Web Locks API across tabs when available. Refresh/login calls are not automatically retried.
- Logout and logout-all are integrated with CSRF headers and local state is cleared even when logout requests fail. Unsupported workspace destinations are shown as unavailable rather than presented as working features.
- Added a quiet health indicator using the existing `/api/v1/health` endpoint and configured API base URL. `frontend/.env.example` documents `VITE_API_BASE_URL` and contains no secrets.
- Added frontend tests for validation, registration, login, safe API errors, protected routing, restoration, refresh/CSRF behavior, refresh failure, refresh deduplication and logout paths.
- No backend authentication behavior was changed. Tests use controlled fetch responses; live browser/backend integration was not run.

Day 5 verification:

- `cd frontend && npm.cmd test -- --reporter=dot`: 2 test files passed, 18 tests passed.
- `cd frontend && npm.cmd run lint`: passed with no reported lint diagnostics.
- `cd frontend && npm.cmd run build`: passed TypeScript project checks and Vite production build (36 modules transformed).
- Manual verification against a running backend and visual checks at desktop, tablet and mobile widths remain necessary.

Known limitations:

- The application has no `/me` endpoint, so restored identity details cannot be populated; dashboard copy avoids inventing them.
- `navigator.locks` is unavailable in some browsers; in those browsers refresh single-flight is limited to the current tab.
- Login and refresh rate limiting must be configured at the production deployment edge/shared limiter; no reliable shared limiter is implemented in this frontend.
- Password recovery, email verification and actual chat/team workspace resources are not implemented.

## Notes

Documentation describes target behavior. Only the completed items above are implemented.
