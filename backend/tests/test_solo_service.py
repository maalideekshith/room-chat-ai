from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.ai.providers import ProviderFailure
from app.models.solo import SoloMessage, SoloWorkspace
from app.models.user import User
from app.solo.service import (
    SoloNotFound,
    create_conversation,
    create_file_source,
    ensure_workspace,
    get_conversation,
    send_message,
)
from app.solo.storage import LocalFileStorage


async def _user(session, name: str) -> User:
    user = User(
        username=f"{name}_{uuid4().hex[:8]}",
        email=f"{name}_{uuid4().hex[:8]}@example.com",
        password_hash="unused-test-hash",
    )
    session.add(user)
    await session.flush()
    return user


@pytest.mark.asyncio
async def test_each_user_gets_one_private_workspace(db_session) -> None:
    user = await _user(db_session, "workspace")
    first = await ensure_workspace(db_session, user.id)
    second = await ensure_workspace(db_session, user.id)
    assert first.id == second.id
    assert first.owner_user_id == user.id
    assert await db_session.scalar(
        select(SoloWorkspace.id).where(SoloWorkspace.owner_user_id == user.id)
    ) == first.id


@pytest.mark.asyncio
async def test_conversation_access_is_scoped_to_owner(db_session) -> None:
    owner = await _user(db_session, "owner")
    stranger = await _user(db_session, "stranger")
    conversation = await create_conversation(db_session, owner.id, "Private", None, None, None)
    assert (await get_conversation(db_session, owner.id, conversation.id)).id == conversation.id
    with pytest.raises(SoloNotFound):
        await get_conversation(db_session, stranger.id, conversation.id)


@pytest.mark.asyncio
async def test_failed_ai_configuration_keeps_the_user_message(db_session) -> None:
    user = await _user(db_session, "message")
    conversation = await create_conversation(db_session, user.id, "New conversation", None, None, None)
    with pytest.raises(ProviderFailure, match="connect_provider_before_chat"):
        await send_message(db_session, user.id, conversation.id, "Keep this question")
    stored = list((await db_session.scalars(
        select(SoloMessage).where(SoloMessage.conversation_id == conversation.id)
    )).all())
    assert [(item.role, item.content) for item in stored] == [("user", "Keep this question")]


@pytest.mark.asyncio
async def test_failed_ingestion_is_recorded_and_upload_object_is_removed(db_session, tmp_path) -> None:
    user = await _user(db_session, "source")
    source = await create_file_source(
        db_session,
        user.id,
        "notes.txt",
        "text/plain",
        b"A small piece of personal knowledge.",
        storage=LocalFileStorage(str(tmp_path)),
    )
    assert source.status == "failed"
    assert source.error_code == "ingestion_failed"
    assert source.processed_at is not None
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.asyncio
async def test_local_storage_delete_removes_file_and_empty_owner_directory() -> None:
    owner_id, source_id = uuid4(), uuid4()
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as temporary_root:
        root = Path(temporary_root)
        storage = LocalFileStorage(str(root))
        key = await storage.put(owner_id, source_id, ".txt", b"private content")
        uploaded_path = root / str(owner_id) / f"{source_id}.txt"

        assert uploaded_path.is_file()
        await storage.delete(key)

        assert not uploaded_path.exists()
        assert list(root.rglob("*")) == []
