import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

import app.db.session as database_session_module
from app.core.config import settings
from app.db.session import get_db_session
from app.main import app


def _load_test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set; database integration tests skipped")
    if not url.startswith("postgresql+asyncpg://"):
        pytest.fail("TEST_DATABASE_URL must use the postgresql+asyncpg:// scheme")

    test_database = make_url(url).database
    application_database = make_url(settings.database_url).database
    if test_database == application_database:
        pytest.fail(
            "TEST_DATABASE_URL points at the application database; "
            "use a separate test database"
        )
    return url


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return _load_test_database_url()


@pytest.fixture(scope="session")
def test_database_name(test_database_url: str) -> str:
    return make_url(test_database_url).database


@pytest_asyncio.fixture
async def test_engine(test_database_url: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        test_database_url,
        poolclass=NullPool,
        connect_args={"timeout": settings.db_connect_timeout},
    )
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def test_session_factory(
    test_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )



@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    connection = await test_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        autoflush=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()


@pytest.fixture
def test_app_db_session(db_session: AsyncSession):
    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        yield db_session
    finally:
        app.dependency_overrides.pop(get_db_session, None)
@pytest.fixture
def test_app_database(
    monkeypatch: pytest.MonkeyPatch,
    test_session_factory: async_sessionmaker[AsyncSession],
) -> async_sessionmaker[AsyncSession]:
    monkeypatch.setattr(database_session_module, "async_session_factory", test_session_factory)
    return test_session_factory


@pytest.fixture(autouse=True)
def guard_application_database(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if "test_app_database" in request.fixturenames:
        return

    def blocked_session_factory() -> None:
        raise RuntimeError(
            "This test attempted to use the application database. "
            "Request the test_app_database fixture so access is routed to "
            "TEST_DATABASE_URL."
        )

    monkeypatch.setattr(database_session_module, "async_session_factory", blocked_session_factory)


@pytest.fixture
def current_database(test_session_factory: async_sessionmaker[AsyncSession]):
    async def read_current_database() -> str:
        async with test_session_factory() as session:
            result = await session.execute(text("SELECT current_database()"))
            return result.scalar_one()

    return read_current_database
