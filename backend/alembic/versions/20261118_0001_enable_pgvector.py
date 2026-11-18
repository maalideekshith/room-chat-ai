"""Enable the pgvector extension.

Revision ID: 20261118_0001
Revises:
Create Date: 2026-11-18
"""

from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "20261118_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    available = connection.execute(
        text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
    ).scalar()
    if available != 1:
        raise RuntimeError(
            "PostgreSQL pgvector extension is not installed on this server. "
            "Install pgvector for PostgreSQL 18, then run 'alembic upgrade head'. "
            "Docker users can use the pgvector/pgvector:pg18 image. "
            "See docs/DATABASE.md for setup instructions."
        )
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS vector")
