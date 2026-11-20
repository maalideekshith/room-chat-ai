from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.user import User


def _user(**overrides: object) -> User:
    values: dict[str, object] = {
        "username": "alice_dev",
        "email": "alice@example.com",
        "password_hash": hash_password("correct horse battery staple"),
    }
    values.update(overrides)
    return User(**values)


@pytest.mark.asyncio
async def test_uuid_is_generated(db_session) -> None:
    user = _user()
    db_session.add(user)
    await db_session.flush()

    assert isinstance(user.id, UUID)


@pytest.mark.asyncio
async def test_timestamps_are_populated(db_session) -> None:
    user = _user()
    db_session.add(user)
    await db_session.flush()

    assert user.created_at is not None
    assert user.updated_at is not None


@pytest.mark.asyncio
async def test_inactive_user_can_be_represented(db_session) -> None:
    user = _user(username="inactive_user", email="inactive@example.com", is_active=False)
    db_session.add(user)
    await db_session.flush()

    stored = await db_session.scalar(select(User).where(User.username == "inactive_user"))
    assert stored is not None
    assert stored.is_active is False


@pytest.mark.asyncio
async def test_required_fields_are_enforced(db_session) -> None:
    db_session.add(User(username=None, email="missing@example.com", password_hash="hash"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_username_must_be_unique(db_session) -> None:
    db_session.add(_user())
    await db_session.flush()
    db_session.add(_user(email="other@example.com"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_email_must_be_unique(db_session) -> None:
    db_session.add(_user())
    await db_session.flush()
    db_session.add(_user(username="other_user"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_username_must_be_lowercase(db_session) -> None:
    db_session.add(_user(username="Alice_Dev"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_email_must_be_lowercase(db_session) -> None:
    db_session.add(_user(email="Alice@Example.com"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_username_length_is_enforced(db_session) -> None:
    db_session.add(_user(username="ab"))

    with pytest.raises(IntegrityError):
        await db_session.flush()
