# Room Chat AI - Database Design

## Status

Day 2 adds the database foundation: async SQLAlchemy 2 engine, session dependency, declarative Base, model registration package, Alembic, and a pgvector extension migration. No business models, authentication, or AI tables exist yet. The entity sections below are the approved target schema direction.

## Day 2 Foundation

Implemented:
- Async SQLAlchemy 2 engine using `asyncpg`.
- Async session factory and FastAPI `get_db_session` dependency.
- Declarative `Base` in `backend/app/db/base.py`.
- Central model registration through `backend/app/models/__init__.py`.
- Alembic async configuration in `backend/alembic/env.py`.
- Initial migration enabling the `vector` extension.
- Liveness `/health` and `/api/v1/health`; database readiness `/api/v1/health/db`.

Not implemented:
- Any business model or table.
- Authentication tables.
- Embedding tables or RAG.

## Environment

Required backend variables:
- `DATABASE_URL` must use `postgresql+asyncpg://`.
- `DB_POOL_SIZE` default 5.
- `DB_MAX_OVERFLOW` default 10.
- `DB_POOL_TIMEOUT` default 30.
- `DB_CONNECT_TIMEOUT` default 5.
- `DB_ECHO` default false.
- `TEST_DATABASE_URL` for integration tests.

Copy `backend/.env.example` to `backend/.env` and replace the password. Never commit `.env`.

## PostgreSQL Setup

With a local PostgreSQL 18 installation:
1. Create a role and databases.
2. Grant ownership.
3. Install pgvector for PostgreSQL 18.
4. Set `DATABASE_URL`.
5. Run `alembic upgrade head` from `backend`.

```sql
CREATE ROLE room_chat LOGIN PASSWORD 'replace-me';
CREATE DATABASE room_chat_ai OWNER room_chat;
CREATE DATABASE room_chat_ai_test OWNER room_chat;
```

## pgvector

The initial migration checks `pg_available_extensions` for `vector`. If the server extension is missing, it raises a clear error instead of silently skipping.

Setup options:
- Docker: use the `pgvector/pgvector:pg18` image.
- Linux package: install the pgvector package matching PostgreSQL 18.
- Windows: install pgvector binaries for PostgreSQL 18 into the server's `lib` and `share/extension` directories.

Verify:

```sql
SELECT * FROM pg_available_extensions WHERE name = 'vector';
```

## Migrations

From `backend/`:

```powershell
.venv\Scripts\activate
alembic upgrade head
alembic current
alembic revision --autogenerate -m "describe change"
alembic downgrade -1
```

Alembic reads `DATABASE_URL` from the same Pydantic Settings used by the app. No credentials are stored in `alembic.ini`.

## Database Tests

From `backend/` with a real PostgreSQL test database:

```powershell
$env:TEST_DATABASE_URL="postgresql+asyncpg://room_chat:replace-me@localhost:5432/room_chat_ai_test"
$env:DATABASE_URL=$env:TEST_DATABASE_URL
.venv\Scripts\python.exe -m pytest
```

Tests that require PostgreSQL skip when `TEST_DATABASE_URL` is unset. pgvector checks skip when the server extension is unavailable. SQLite is not used as a substitute.

## Conventions

- UUID primary keys.
- UTC timestamps.
- Every room/conversation-scoped table includes its scope key.
- Foreign keys enforced; no orphan room, conversation or source data.
- Soft delete only where history or recovery is required; otherwise hard delete with cascade cleanup.
- Unique constraints are explicit and indexed.
- Embedding metadata is versioned.

## Identity and Sessions

### users

- `id` UUID, immutable platform user ID.
- `email` unique, normalized.
- `username` unique, normalized.
- `password_hash` Argon2id.
- `status`, `created_at`, `updated_at`.

### refresh_sessions

- `id`, `user_id`, `token_hash`, `family_id`.
- `issued_at`, `expires_at`, `rotated_at`, `revoked_at`, `replaced_by_id`.
- `user_agent`, `ip_hash` for security review.
- Reuse of a rotated token revokes the family.

## Workspaces and Rooms

### workspaces

- `id`, `type` (`solo` | `team`), `name`, `owner_user_id`.
- Exactly one `solo` workspace per user (unique partial index on `owner_user_id` where type = solo).
- Personal workspace access is owner-only.

### rooms

- `id`, `workspace_id`, `type` (`team`), `name`, `created_by`.
- Archive state and timestamps.
- Solo does not require a room row; Solo uses workspace-scoped conversations.

### room_members

- `room_id`, `user_id`, `role` (`owner` | `admin` | `member`).
- Unique `(room_id, user_id)`.
- Active membership count must not exceed 10 including the owner.
- `left_at` for history; leaving frees a slot.

### invitations

- `id`, `room_id`, `email`, `role`, `token_hash`.
- `invited_by`, `status`, `expires_at`, `accepted_at`.
- Pending invitations reserve capacity.
- Acceptance re-checks capacity transactionally.

## Conversations and Messages

### conversations

- `id`, `workspace_id`.
- `type` (`direct` | `team`).
- `room_id` nullable, required for `team`, forbidden for `direct`.
- `created_by`, `title`, `last_message_at`, `deleted_at`.
- AI selection fields: `ai_provider`, `ai_credential_id`, `ai_model`.
- Switching provider/model updates these fields without deleting history.

### conversation_participants

- `conversation_id`, `user_id`, `joined_at`, `left_at`.
- Direct conversations must have exactly two active participants.
- Team conversations inherit room membership authorization.

### messages

- `id`, `conversation_id`, `sender_id`, `kind`, `body`.
- Optional `parent_message_id`.
- Indexed by `(conversation_id, created_at)`.
- Shared table for direct and team conversations.

### conversation_ai_state

Optional per-conversation AI settings snapshot:
- `conversation_id`, `provider`, `credential_id`, `model`.
- Kept for history and reproducibility; current selection lives on `conversations`.

## Files, Sources and Embeddings

### files

- `id`, `workspace_id`, `conversation_id`/`room_id`, `uploader_id`.
- `filename`, `mime_type`, `size_bytes`, `checksum`, `storage_key`.
- `storage_backend` (`local` | `s3`).
- `status` (`pending` | `ready` | `failed` | `deleted`).

### sources

- `id`, `workspace_id`, `conversation_id`/`room_id`, `kind` (`file` | `url`), `file_id`, `url`.
- `title`, `metadata`, `status`, `fetched_at`.
- Immutable snapshot; re-ingestion creates a new version.

### document_chunks

- `id`, `source_id`, `workspace_id`, `conversation_id`/`room_id`, `content`, `token_count`.
- `embedding_provider`, `embedding_model`, `embedding_version`, `embedding_dimensions`.
- `embedding` pgvector column.
- Indexed for similarity search scoped to the authorized scope.

### extraction_jobs

- `id`, `source_id`, `kind`, `status`, `attempts`, `error_code`, timestamps.
- Tracks OCR and text extraction pipeline state.

## AI Credentials and Preferences

### ai_credentials

- `id`, `user_id`, `provider` (`openai` | `anthropic` | `gemini`).
- `label`, `encrypted_dek`, `encrypted_key`, `key_last4`.
- `key_version`, `status` (`active` | `invalid` | `revoked`).
- `last_validated_at`, `created_at`, `revoked_at`.
- Multiple rows per user and provider allowed.
- No plaintext key column.
- Unique `(user_id, provider, label)`.

### user_ai_preferences

- `user_id` primary key.
- `default_provider`, `default_credential_id`, `default_model`.
- Defaults only; each conversation may override.

### ai_runs

- `id`, `user_id`, `workspace_id`, `conversation_id`, `report_id` nullable.
- `provider`, `credential_id`, `model`.
- Token usage, latency, status, error code.
- Source reference list.
- No plaintext credential data.

## Collaboration and Product Data

### reports

- `id`, `workspace_id`, `conversation_id`/`room_id`, `generated_by`, `kind`.
- Structured content, status, model metadata, source references, timestamps.

### activity_events

- `id`, `workspace_id`, `room_id`, `actor_id`, `event_type`, `payload`, `created_at`.
- Append-only for room history.

### notifications

- `id`, `user_id`, `workspace_id`, `type`, `payload`, `read_at`, `created_at`.

### email_outbox

- `id`, `to_email`, `template`, `payload`, `status`, `attempts`, `sent_at`.
- Provider-independent send attempt tracking.

### usage_events

- `id`, `user_id`, `workspace_id`, `metric`, `quantity`, `occurred_at`, `metadata`.

### subscriptions and entitlements (future)

- `subscriptions`: user/workspace, plan, status, period.
- `entitlements`: plan limits and feature flags.
- Not implemented; schema must not block them.

## Deletion Behavior

- Deleting a conversation deletes its messages and conversation-scoped sources.
- Deleting a source deletes its chunks, embeddings and extraction jobs.
- Deleting a file marks the record deleted and removes the storage object.
- Derived AI runs keep usage metadata but not deleted content.
- Security/audit records follow a separate retention policy.

## Isolation Rules

- Repository methods require an explicit scope.
- Authorization is checked before repository access.
- Retrieval always filters by authorized workspace/conversation/room.
- AI credentials load only for the owning user.
- Optional PostgreSQL row-level security can be added as defense in depth.

## Capacity Rules

- Room row locked during invite acceptance and membership changes.
- Active members plus pending invitations must not exceed 10.
- Owner transfer is required before owner leaves.

## Open Schema Decisions

- Exact soft-delete window for user content.
- Whether extraction jobs need a separate queue table once Celery is added.
- Audit retention duration and legal hold policy.
