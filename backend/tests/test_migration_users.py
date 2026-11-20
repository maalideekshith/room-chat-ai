import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_users_table_exists(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(text("SELECT to_regclass('public.users')"))
        assert result.scalar_one() == "users"


@pytest.mark.asyncio
async def test_users_table_columns(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'users'"
            )
        )
        columns = {row[0] for row in result}

    assert columns == {
        "id",
        "username",
        "email",
        "password_hash",
        "is_active",
        "email_verified_at",
        "last_login_at",
        "created_at",
        "updated_at",
    }


@pytest.mark.asyncio
async def test_database_is_at_day_6_migration_head(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(text("SELECT version_num FROM alembic_version"))
    assert result.scalar_one() == "20261121_0004"


@pytest.mark.asyncio
async def test_refresh_sessions_table_has_required_columns(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'refresh_sessions'"
            )
        )
        columns = {row[0] for row in result}
    assert columns == {
        "id", "user_id", "token_hash", "family_id", "issued_at", "expires_at",
        "rotated_at", "revoked_at", "replaced_by_id",
    }


@pytest.mark.asyncio
async def test_refresh_sessions_constraints_and_indexes_exist(test_session_factory) -> None:
    async with test_session_factory() as session:
        constraints = await session.execute(
            text(
                "SELECT conname FROM pg_constraint "
                "WHERE conrelid = 'public.refresh_sessions'::regclass"
            )
        )
        indexes = await session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE schemaname = 'public' AND tablename = 'refresh_sessions'"
            )
        )
    constraint_names = {row[0] for row in constraints}
    index_names = {row[0] for row in indexes}
    assert "ck_refresh_sessions_expiry_after_issue" in constraint_names
    assert "uq_refresh_sessions_token_hash" in constraint_names
    assert {
        "ix_refresh_sessions_user_id",
        "ix_refresh_sessions_family_id",
        "ix_refresh_sessions_expires_at",
    } <= index_names
