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

Verified:
- Backend tests: 2 passed.
- Frontend build: passed.

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

- Authentication and sessions.
- Database models, PostgreSQL and pgvector.
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

## Next

### Day 2

- Database foundation with PostgreSQL and pgvector.
- Alembic baseline.
- Initial schema and migration structure.

## Notes

Documentation describes target behavior. Only the Day 1 items above are implemented.
