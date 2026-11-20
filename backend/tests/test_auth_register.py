from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import verify_password
from app.main import app
from app.models.user import User
from app.models.solo import SoloWorkspace

VALID_PASSWORD = "correct horse battery staple"


def _payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "username": "alice_dev",
        "email": "alice@example.com",
        "password": VALID_PASSWORD,
    }
    payload.update(overrides)
    return payload


async def _register(client: AsyncClient, payload: dict[str, object]):
    return await client.post("/api/v1/auth/register", json=payload)


@pytest.mark.asyncio
async def test_valid_registration_returns_201(test_app_db_session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _register(client, _payload())

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "username", "email", "is_active", "created_at"}
    assert body["username"] == "alice_dev"
    assert body["email"] == "alice@example.com"
    assert body["is_active"] is True
    workspace = await test_app_db_session.scalar(
        select(SoloWorkspace).where(SoloWorkspace.owner_user_id == UUID(body["id"]))
    )
    assert workspace is not None


@pytest.mark.asyncio
async def test_registration_never_returns_password(test_app_db_session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _register(client, _payload())

    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    assert VALID_PASSWORD not in response.text


@pytest.mark.asyncio
async def test_username_and_email_are_normalized(test_app_db_session) -> None:
    payload = _payload(username="  Alice_Dev  ", email="  Alice@Example.COM  ")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _register(client, payload)

    assert response.status_code == 201
    assert response.json()["username"] == "alice_dev"
    assert response.json()["email"] == "alice@example.com"


@pytest.mark.asyncio
async def test_stored_hash_verifies_submitted_password(test_app_db_session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _register(client, _payload())

    assert response.status_code == 201
    user = await test_app_db_session.scalar(
        select(User).where(User.username == "alice_dev")
    )
    assert user is not None
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(VALID_PASSWORD, user.password_hash) is True


@pytest.mark.asyncio
async def test_duplicate_username_returns_409(test_app_db_session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await _register(client, _payload())
        second = await _register(
            client,
            _payload(username="alice_dev", email="other@example.com"),
        )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "Username or email is already registered"}


@pytest.mark.asyncio
async def test_duplicate_username_different_case_returns_409(test_app_db_session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await _register(client, _payload())
        second = await _register(
            client,
            _payload(username="ALICE_DEV", email="other@example.com"),
        )

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_duplicate_email_different_case_returns_409(test_app_db_session) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await _register(client, _payload())
        second = await _register(
            client,
            _payload(username="other_user", email="ALICE@EXAMPLE.COM"),
        )

    assert first.status_code == 201
    assert second.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "username",
    ["ab", "a" * 31, "bad name", "bad-name", "álîce", "alice!"],
)
async def test_invalid_username_returns_422(test_app_db_session, username: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _register(client, _payload(username=username))

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("email", ["not-an-email", "missing@", "@example.com"])
async def test_invalid_email_returns_422(test_app_db_session, email: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _register(client, _payload(email=email))

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password",
    ["short", "            ", "a" * 129],
)
async def test_invalid_password_returns_422(test_app_db_session, password: str) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await _register(client, _payload(password=password))

    assert response.status_code == 422
