"""Create personal Solo workspaces, conversations, credentials and sources.

Revision ID: 20261121_0004
Revises: 20261120_0003
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261121_0004"
down_revision: str | None = "20261120_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE solo_workspaces (
            id UUID PRIMARY KEY,
            owner_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_solo_workspaces_owner UNIQUE(owner_user_id),
            CONSTRAINT uq_solo_workspaces_id_owner UNIQUE(id, owner_user_id)
        )
    """)
    op.execute("""
        INSERT INTO solo_workspaces (id, owner_user_id)
        SELECT gen_random_uuid(), id FROM users
    """)
    op.execute("""
        CREATE TABLE ai_credentials (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            provider VARCHAR(20) NOT NULL CONSTRAINT ck_ai_credentials_provider CHECK (provider IN ('openai','anthropic','gemini')),
            label VARCHAR(80) NOT NULL,
            encrypted_dek BYTEA NOT NULL,
            encrypted_key BYTEA NOT NULL,
            key_suffix VARCHAR(4) NOT NULL,
            status VARCHAR(16) NOT NULL DEFAULT 'active' CONSTRAINT ck_ai_credentials_status CHECK (status IN ('active','invalid','revoked')),
            last_validated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            revoked_at TIMESTAMPTZ,
            CONSTRAINT uq_ai_credentials_id_user UNIQUE(id,user_id),
            CONSTRAINT uq_ai_credentials_user_provider_label UNIQUE(user_id,provider,label)
        )
    """)
    op.execute("CREATE INDEX ix_ai_credentials_user_id ON ai_credentials(user_id)")
    op.execute("""
        CREATE TABLE user_ai_preferences (
            user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
            default_provider VARCHAR(20) CONSTRAINT ck_ai_preferences_provider CHECK (default_provider IS NULL OR default_provider IN ('openai','anthropic','gemini')),
            default_credential_id UUID,
            default_model VARCHAR(100),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT ck_ai_preferences_complete_default CHECK (
                (default_provider IS NULL AND default_credential_id IS NULL AND default_model IS NULL) OR
                (default_provider IS NOT NULL AND default_credential_id IS NOT NULL AND default_model IS NOT NULL)
            ),
            CONSTRAINT fk_ai_preferences_credential_owner FOREIGN KEY(default_credential_id,user_id)
                REFERENCES ai_credentials(id,user_id)
        )
    """)
    op.execute("""
        CREATE TABLE solo_conversations (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL,
            user_id UUID NOT NULL,
            title VARCHAR(160) NOT NULL DEFAULT 'New conversation',
            ai_provider VARCHAR(20) CONSTRAINT ck_solo_conversations_provider CHECK (ai_provider IS NULL OR ai_provider IN ('openai','anthropic','gemini')),
            ai_credential_id UUID,
            ai_model VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_solo_conversations_id_user UNIQUE(id,user_id),
            CONSTRAINT fk_solo_conversations_workspace_owner FOREIGN KEY(workspace_id,user_id)
                REFERENCES solo_workspaces(id,owner_user_id) ON DELETE CASCADE,
            CONSTRAINT fk_solo_conversations_credential_owner FOREIGN KEY(ai_credential_id,user_id)
                REFERENCES ai_credentials(id,user_id),
            CONSTRAINT ck_solo_conversations_complete_ai_settings CHECK (
                (ai_provider IS NULL AND ai_credential_id IS NULL AND ai_model IS NULL) OR
                (ai_provider IS NOT NULL AND ai_credential_id IS NOT NULL AND ai_model IS NOT NULL)
            )
        )
    """)
    op.execute("CREATE INDEX ix_solo_conversations_user_updated ON solo_conversations(user_id,updated_at)")
    op.execute("""
        CREATE TABLE solo_messages (
            id UUID PRIMARY KEY,
            conversation_id UUID NOT NULL,
            user_id UUID NOT NULL,
            role VARCHAR(12) NOT NULL CONSTRAINT ck_solo_messages_role CHECK (role IN ('user','assistant')),
            content TEXT NOT NULL,
            source_refs JSONB NOT NULL DEFAULT '[]'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_solo_messages_conversation_owner FOREIGN KEY(conversation_id,user_id)
                REFERENCES solo_conversations(id,user_id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX ix_solo_messages_conversation_created ON solo_messages(conversation_id,created_at)")
    op.execute("""
        CREATE TABLE solo_sources (
            id UUID PRIMARY KEY,
            workspace_id UUID NOT NULL,
            user_id UUID NOT NULL,
            kind VARCHAR(12) NOT NULL CONSTRAINT ck_solo_sources_kind CHECK (kind IN ('file','url')),
            title VARCHAR(240) NOT NULL,
            url TEXT,
            storage_key VARCHAR(200),
            mime_type VARCHAR(120),
            size_bytes INTEGER CONSTRAINT ck_solo_sources_size_bytes CHECK (size_bytes IS NULL OR size_bytes >= 0),
            checksum VARCHAR(64),
            status VARCHAR(16) NOT NULL DEFAULT 'processing' CONSTRAINT ck_solo_sources_status CHECK (status IN ('processing','ready','failed')),
            error_code VARCHAR(40),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            processed_at TIMESTAMPTZ,
            CONSTRAINT uq_solo_sources_id_user UNIQUE(id,user_id),
            CONSTRAINT fk_solo_sources_workspace_owner FOREIGN KEY(workspace_id,user_id)
                REFERENCES solo_workspaces(id,owner_user_id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX ix_solo_sources_user_created ON solo_sources(user_id,created_at)")
    op.execute("""
        CREATE TABLE document_chunks (
            id UUID PRIMARY KEY,
            source_id UUID NOT NULL,
            user_id UUID NOT NULL,
            ordinal INTEGER NOT NULL CONSTRAINT ck_document_chunks_ordinal CHECK (ordinal >= 0),
            content TEXT NOT NULL,
            embedding vector(768) NOT NULL,
            embedding_provider VARCHAR(20) NOT NULL,
            embedding_model VARCHAR(100) NOT NULL,
            embedding_version VARCHAR(40) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fk_document_chunks_source_owner FOREIGN KEY(source_id,user_id)
                REFERENCES solo_sources(id,user_id) ON DELETE CASCADE,
            CONSTRAINT uq_document_chunks_source_ordinal UNIQUE(source_id,ordinal)
        )
    """)
    op.execute("CREATE INDEX ix_document_chunks_user_id ON document_chunks(user_id)")
    op.execute("CREATE INDEX ix_document_chunks_source_id ON document_chunks(source_id)")
    op.execute("""
        CREATE INDEX ix_document_chunks_embedding_cosine
        ON document_chunks USING hnsw (embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE document_chunks")
    op.execute("DROP TABLE solo_sources")
    op.execute("DROP TABLE solo_messages")
    op.execute("DROP TABLE solo_conversations")
    op.execute("DROP TABLE user_ai_preferences")
    op.execute("DROP TABLE ai_credentials")
    op.execute("DROP TABLE solo_workspaces")
