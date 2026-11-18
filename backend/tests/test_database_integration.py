import pytest
from sqlalchemy import text

from app.db.session import get_db_session

pytestmark = pytest.mark.usefixtures("test_app_database")


@pytest.mark.asyncio
async def test_database_connection(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_session_dependency_lifecycle() -> None:
    dependency = get_db_session()
    session = await anext(dependency)

    result = await session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1
    assert session.in_transaction() is True

    await dependency.aclose()
    assert session.in_transaction() is False


@pytest.mark.asyncio
async def test_application_uses_test_database(test_database_name: str) -> None:
    dependency = get_db_session()
    session = await anext(dependency)

    try:
        result = await session.execute(text("SELECT current_database()"))
        assert result.scalar_one() == test_database_name
    finally:
        await dependency.aclose()


@pytest.mark.asyncio
async def test_pgvector_extension_available(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(
            text("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'")
        )
        if result.scalar() != 1:
            pytest.skip("pgvector server extension is not installed")


@pytest.mark.asyncio
async def test_pgvector_extension_enabled(test_session_factory) -> None:
    async with test_session_factory() as session:
        result = await session.execute(
            text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        )
        if result.scalar() != 1:
            pytest.skip("pgvector extension has not been enabled")


@pytest.mark.asyncio
async def test_readiness_endpoint_ok() -> None:
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
