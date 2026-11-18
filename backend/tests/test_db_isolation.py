import pytest
from sqlalchemy import text

import app.db.session as db_session


def test_application_database_is_blocked_without_test_fixture() -> None:
    with pytest.raises(RuntimeError, match="test_app_database"):
        db_session.async_session_factory()


@pytest.mark.asyncio
async def test_test_fixture_routes_application_factory_to_test_database(
    test_app_database,
    test_database_name: str,
) -> None:
    async with test_app_database() as session:
        result = await session.execute(text("SELECT current_database()"))
        assert result.scalar_one() == test_database_name
