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

### Verification Snapshot

- PostgreSQL 18.7 via Docker; pgvector 0.8.7.
- Main and test databases at revision `20261119_0002`.
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

- JWT authentication sessions, login, refresh tokens and password reset.
- Business database models and tables beyond users.
- Solo workspace features.
- Team rooms, memberships, invitations, roles.
- Notifications and email delivery.
- Direct chat and WebSockets.
- File uploads and ingestion.
- AI providers, BYOK, encryption and RAG.
- Reports.
- MCP, Redis, Celery.
- Billing and subscriptions.
- Docker deployment.

## Manual Setup Required

- Keep the Docker PostgreSQL container running for database integration tests.
- Set `DATABASE_URL` and `TEST_DATABASE_URL` in `backend/.env` for local development and testing.
- No Day 3 migration work remains; revision `20261119_0002` is applied to both databases.

## Next

### Day 4

- JWT access tokens.
- Refresh sessions, rotation and revocation.

## Notes

Documentation describes target behavior. Only the completed items above are implemented.
