import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings


def test_database_url_uses_asyncpg() -> None:
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_pool_defaults_are_sane() -> None:
    assert settings.db_pool_size >= 1
    assert settings.db_max_overflow >= 0
    assert settings.db_pool_timeout > 0
    assert settings.db_connect_timeout > 0


def test_rejects_non_asyncpg_database_url() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url="postgresql://localhost:5432/room_chat_ai")
