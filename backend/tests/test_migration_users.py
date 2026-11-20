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
async def test_database_is_at_users_migration(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(text("SELECT version_num FROM alembic_version"))
        assert result.scalar_one() == "20261119_0002"
