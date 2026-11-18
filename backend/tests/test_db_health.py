import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.health import database_is_ready
from app.db.session import get_db_session
from app.main import app

BAD_DATABASE_URL = "postgresql+asyncpg://postgres@127.0.0.1:1/room_chat_ai"


@pytest.mark.asyncio
async def test_database_is_not_ready_when_unreachable() -> None:
    engine = create_async_engine(BAD_DATABASE_URL, connect_args={"timeout": 1})
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with factory() as session:
        assert await database_is_ready(session) is False

    await engine.dispose()


def test_readiness_endpoint_returns_503_when_database_unavailable() -> None:
    async def unavailable_session():
        engine = create_async_engine(BAD_DATABASE_URL, connect_args={"timeout": 1})
        factory = async_sessionmaker(bind=engine, expire_on_commit=False)
        try:
            async with factory() as session:
                yield session
        finally:
            await engine.dispose()

    app.dependency_overrides[get_db_session] = unavailable_session
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/db")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "unavailable"}
