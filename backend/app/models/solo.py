from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EMBEDDING_DIMENSIONS = 768


class SoloWorkspace(Base):
    __tablename__ = "solo_workspaces"
    __table_args__ = (
        UniqueConstraint("owner_user_id", name="uq_solo_workspaces_owner"),
        UniqueConstraint("id", "owner_user_id", name="uq_solo_workspaces_id_owner"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AiCredential(Base):
    __tablename__ = "ai_credentials"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_ai_credentials_id_user"),
        UniqueConstraint("user_id", "provider", "label", name="uq_ai_credentials_user_provider_label"),
        CheckConstraint("provider IN ('openai', 'anthropic', 'gemini')", name="ck_ai_credentials_provider"),
        CheckConstraint("status IN ('active', 'invalid', 'revoked')", name="ck_ai_credentials_status"),
        Index("ix_ai_credentials_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    encrypted_dek: Mapped[bytes] = mapped_column(nullable=False)
    encrypted_key: Mapped[bytes] = mapped_column(nullable=False)
    key_suffix: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'active'"))
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserAiPreference(Base):
    __tablename__ = "user_ai_preferences"
    __table_args__ = (
        CheckConstraint(
            "default_provider IS NULL OR default_provider IN ('openai', 'anthropic', 'gemini')",
            name="ck_ai_preferences_provider",
        ),
        ForeignKeyConstraint(
            ["default_credential_id", "user_id"],
            ["ai_credentials.id", "ai_credentials.user_id"],
            name="fk_ai_preferences_credential_owner",
        ),
        CheckConstraint(
            "(default_provider IS NULL AND default_credential_id IS NULL AND default_model IS NULL) "
            "OR (default_provider IS NOT NULL AND default_credential_id IS NOT NULL AND default_model IS NOT NULL)",
            name="ck_ai_preferences_complete_default",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    default_provider: Mapped[str | None] = mapped_column(String(20))
    default_credential_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True)
    )
    default_model: Mapped[str | None] = mapped_column(String(100))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SoloConversation(Base):
    __tablename__ = "solo_conversations"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_solo_conversations_id_user"),
        ForeignKeyConstraint(
            ["workspace_id", "user_id"],
            ["solo_workspaces.id", "solo_workspaces.owner_user_id"],
            ondelete="CASCADE",
            name="fk_solo_conversations_workspace_owner",
        ),
        ForeignKeyConstraint(
            ["ai_credential_id", "user_id"],
            ["ai_credentials.id", "ai_credentials.user_id"],
            name="fk_solo_conversations_credential_owner",
        ),
        CheckConstraint(
            "ai_provider IS NULL OR ai_provider IN ('openai', 'anthropic', 'gemini')",
            name="ck_solo_conversations_provider",
        ),
        CheckConstraint(
            "(ai_provider IS NULL AND ai_credential_id IS NULL AND ai_model IS NULL) "
            "OR (ai_provider IS NOT NULL AND ai_credential_id IS NOT NULL AND ai_model IS NOT NULL)",
            name="ck_solo_conversations_complete_ai_settings",
        ),
        Index("ix_solo_conversations_user_updated", "user_id", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False, server_default=text("'New conversation'"))
    ai_provider: Mapped[str | None] = mapped_column(String(20))
    ai_credential_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True)
    )
    ai_model: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SoloMessage(Base):
    __tablename__ = "solo_messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["conversation_id", "user_id"],
            ["solo_conversations.id", "solo_conversations.user_id"],
            ondelete="CASCADE",
            name="fk_solo_messages_conversation_owner",
        ),
        CheckConstraint("role IN ('user', 'assistant')", name="ck_solo_messages_role"),
        Index("ix_solo_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(12), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SoloSource(Base):
    __tablename__ = "solo_sources"
    __table_args__ = (
        UniqueConstraint("id", "user_id", name="uq_solo_sources_id_user"),
        ForeignKeyConstraint(
            ["workspace_id", "user_id"],
            ["solo_workspaces.id", "solo_workspaces.owner_user_id"],
            ondelete="CASCADE",
            name="fk_solo_sources_workspace_owner",
        ),
        CheckConstraint("kind IN ('file', 'url')", name="ck_solo_sources_kind"),
        CheckConstraint("status IN ('processing', 'ready', 'failed')", name="ck_solo_sources_status"),
        CheckConstraint("size_bytes IS NULL OR size_bytes >= 0", name="ck_solo_sources_size_bytes"),
        Index("ix_solo_sources_user_created", "user_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    kind: Mapped[str] = mapped_column(String(12), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    storage_key: Mapped[str | None] = mapped_column(String(200))
    mime_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'processing'"))
    error_code: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_id", "user_id"],
            ["solo_sources.id", "solo_sources.user_id"],
            ondelete="CASCADE",
            name="fk_document_chunks_source_owner",
        ),
        Index("ix_document_chunks_user_id", "user_id"),
        Index("ix_document_chunks_source_id", "source_id"),
        Index(
            "ix_document_chunks_embedding_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        UniqueConstraint("source_id", "ordinal", name="uq_document_chunks_source_ordinal"),
        CheckConstraint("ordinal >= 0", name="ck_document_chunks_ordinal"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    embedding_provider: Mapped[str] = mapped_column(String(20), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
