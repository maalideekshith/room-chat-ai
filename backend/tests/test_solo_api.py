from uuid import uuid4
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_current_user
from app.db.session import get_db_session
from app.main import app
from app.models.solo import AiCredential, SoloConversation, UserAiPreference
from app.models.user import User
from app.schemas.solo import ConversationResponse
from app.solo.service import create_conversation


def _use_user_and_session(monkeypatch, session, user: User) -> None:
    async def session_override():
        yield session

    async def user_override():
        return user

    monkeypatch.setitem(app.dependency_overrides, get_db_session, session_override)
    monkeypatch.setitem(app.dependency_overrides, get_current_user, user_override)


async def _make_user(session, label: str) -> User:
    unique_id = uuid4().hex
    safe_label = "".join(
        character for character in label.lower()
        if character.isascii() and character.isalnum()
    )[:8] or "user"
    username = f"sc_{safe_label}_{unique_id[:16]}"
    email = f"{safe_label}-{unique_id}@example.com"
    user = User(
        username=username,
        email=email,
        password_hash="unused-test-hash",
    )
    assert len(username) <= 30
    assert len(email) <= 320
    session.add(user)
    await session.flush()
    return user


def _credential(user: User, *, provider: str = "openai") -> AiCredential:
    return AiCredential(
        user_id=user.id,
        provider=provider,
        label="Test credential",
        encrypted_dek=b"test-encrypted-dek",
        encrypted_key=b"test-encrypted-key",
        key_suffix="4321",
    )


@pytest.mark.asyncio
async def test_make_user_generates_unique_values_within_database_limits() -> None:
    class UserCollector:
        def __init__(self) -> None:
            self.users: list[User] = []

        def add(self, user: User) -> None:
            self.users.append(user)

        async def flush(self) -> None:
            return None

    session = UserCollector()
    first = await _make_user(session, "A very long / unsafe test label")
    second = await _make_user(session, "A very long / unsafe test label")

    assert 3 <= len(first.username) <= 30
    assert 3 <= len(second.username) <= 30
    assert len(first.email) <= 320
    assert len(second.email) <= 320
    assert first.username.islower() and second.username.islower()
    assert first.email.islower() and second.email.islower()
    assert first.username != second.username
    assert first.email != second.email


def test_conversation_response_maps_orm_provider_fields() -> None:
    credential_id = uuid4()
    now = datetime.now(timezone.utc)
    conversation = SoloConversation(
        id=uuid4(),
        workspace_id=uuid4(),
        user_id=uuid4(),
        title="Configured",
        ai_provider="openai",
        ai_credential_id=credential_id,
        ai_model="gpt-test-model",
        created_at=now,
        updated_at=now,
    )

    response = ConversationResponse.model_validate(conversation)

    assert response.provider == "openai"
    assert response.credential_id == credential_id
    assert response.model == "gpt-test-model"
    assert response.model_dump()["provider"] == "openai"


@pytest.mark.asyncio
async def test_solo_api_hides_another_users_conversation(test_app_db_session) -> None:
    owner = User(
        username=f"solo_owner_{uuid4().hex[:8]}",
        email=f"solo_owner_{uuid4().hex[:8]}@example.com",
        password_hash="unused-test-hash",
    )
    stranger = User(
        username=f"solo_stranger_{uuid4().hex[:8]}",
        email=f"solo_stranger_{uuid4().hex[:8]}@example.com",
        password_hash="unused-test-hash",
    )
    test_app_db_session.add_all([owner, stranger])
    await test_app_db_session.flush()
    conversation = await create_conversation(
        test_app_db_session, owner.id, "Private", None, None, None
    )

    async def session_override():
        yield test_app_db_session

    async def user_override():
        return stranger

    app.dependency_overrides[get_db_session] = session_override
    app.dependency_overrides[get_current_user] = user_override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(f"/api/v1/solo/conversations/{conversation.id}")
            message_response = await client.get(
                f"/api/v1/solo/conversations/{conversation.id}/messages"
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(get_current_user, None)

    assert response.status_code == 404
    assert message_response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}


@pytest.mark.asyncio
async def test_conversation_create_list_get_and_update_response_fields(
    test_app_db_session, monkeypatch
) -> None:
    user = await _make_user(test_app_db_session, "conversation-shape")
    _use_user_and_session(monkeypatch, test_app_db_session, user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        created = await client.post(
            "/api/v1/solo/conversations", json={"title": "Personal notes"}
        )
        assert created.status_code == 201
        payload = created.json()
        expected_fields = {
            "id", "title", "provider", "credential_id", "model", "created_at", "updated_at"
        }
        assert set(payload) == expected_fields
        assert payload["title"] == "Personal notes"
        assert payload["provider"] is None
        assert payload["credential_id"] is None
        assert payload["model"] is None

        listed = await client.get("/api/v1/solo/conversations")
        retrieved = await client.get(f"/api/v1/solo/conversations/{payload['id']}")
        renamed = await client.patch(
            f"/api/v1/solo/conversations/{payload['id']}",
            json={"title": "Renamed notes"},
        )
        cleared_settings = await client.put(
            f"/api/v1/solo/conversations/{payload['id']}/ai-settings",
            json={"provider": None, "credential_id": None, "model": None},
        )

    assert listed.status_code == retrieved.status_code == 200
    assert set(listed.json()[0]) == expected_fields
    assert retrieved.json() == payload
    assert renamed.status_code == cleared_settings.status_code == 200
    assert set(renamed.json()) == set(cleared_settings.json()) == expected_fields
    assert renamed.json()["title"] == "Renamed notes"
    assert cleared_settings.json()["provider"] is None


@pytest.mark.asyncio
async def test_conversation_creation_returns_explicit_provider_configuration(
    test_app_db_session, monkeypatch
) -> None:
    import app.solo.service as solo_service

    user = await _make_user(test_app_db_session, "explicit-provider")
    credential = _credential(user)
    test_app_db_session.add(credential)
    await test_app_db_session.flush()
    _use_user_and_session(monkeypatch, test_app_db_session, user)

    async def validate_model(session, user_id, credential_id, provider, model):
        assert session is test_app_db_session
        assert user_id == user.id
        assert credential_id == credential.id
        assert provider == "openai"
        assert model == "gpt-test-model"
        return credential

    monkeypatch.setattr(solo_service, "validate_model", validate_model)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/solo/conversations",
            json={
                "title": "Configured conversation",
                "provider": "openai",
                "credential_id": str(credential.id),
                "model": "gpt-test-model",
            },
        )

    assert response.status_code == 201
    assert response.json()["provider"] == "openai"
    assert response.json()["credential_id"] == str(credential.id)
    assert response.json()["model"] == "gpt-test-model"
    assert "encrypted_key" not in response.text


@pytest.mark.asyncio
async def test_conversation_creation_rejects_another_users_credential(
    test_app_db_session, monkeypatch
) -> None:
    owner = await _make_user(test_app_db_session, "credential-owner")
    stranger = await _make_user(test_app_db_session, "credential-stranger")
    credential = _credential(owner)
    test_app_db_session.add(credential)
    await test_app_db_session.flush()
    _use_user_and_session(monkeypatch, test_app_db_session, stranger)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/solo/conversations",
            json={
                "title": "Must not attach another user's key",
                "provider": "openai",
                "credential_id": str(credential.id),
                "model": "gpt-test-model",
            },
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Resource not found"}


@pytest.mark.asyncio
async def test_conversation_creation_rejects_incomplete_provider_selection(
    test_app_db_session, monkeypatch
) -> None:
    user = await _make_user(test_app_db_session, "incomplete-provider")
    _use_user_and_session(monkeypatch, test_app_db_session, user)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/solo/conversations",
            json={"title": "Incomplete selection", "provider": "openai"},
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Choose a provider, credential, and model together."
    }


@pytest.mark.asyncio
async def test_conversation_uses_owner_default_configuration_for_message_resolution(
    db_session,
) -> None:
    import app.solo.service as solo_service

    user = await _make_user(db_session, "default-provider")
    conversation = await create_conversation(
        db_session, user.id, "Uses default", None, None, None
    )
    credential = _credential(user, provider="gemini")
    db_session.add(credential)
    await db_session.flush()
    db_session.add(UserAiPreference(
        user_id=user.id,
        default_provider="gemini",
        default_credential_id=credential.id,
        default_model="gemini-test-model",
    ))
    await db_session.flush()

    resolved = await solo_service._resolve_chat(db_session, user.id, conversation)

    assert resolved == (credential, "gemini", "gemini-test-model")
