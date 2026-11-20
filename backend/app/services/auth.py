import asyncio
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


class RegistrationConflictError(Exception):
    pass


class AuthenticationError(Exception):
    pass


_DUMMY_PASSWORD_HASH = None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def _new_refresh_session(user_id: uuid.UUID, family_id: uuid.UUID) -> tuple[RefreshSession, str]:
    token = _new_refresh_token()
    now = datetime.now(timezone.utc)
    session = RefreshSession(
        user_id=user_id,
        family_id=family_id,
        token_hash=_token_hash(token),
        issued_at=now,
        expires_at=now + timedelta(days=settings.refresh_token_days),
    )
    return session, token


async def login_user(session: AsyncSession, payload: LoginRequest) -> tuple[User, str, int, str]:
    global _DUMMY_PASSWORD_HASH
    identifier = payload.username_or_email
    lookup = User.email == identifier if "@" in identifier else User.username == identifier
    user = await session.scalar(select(User).where(lookup))

    if _DUMMY_PASSWORD_HASH is None:
        _DUMMY_PASSWORD_HASH = await asyncio.to_thread(hash_password, "not-a-real-user-password")
    password_ok = await asyncio.to_thread(
        verify_password,
        payload.password.get_secret_value(),
        user.password_hash if user is not None else _DUMMY_PASSWORD_HASH,
    )
    if user is None or not password_ok or not user.is_active:
        await session.rollback()
        raise AuthenticationError

    user.last_login_at = datetime.now(timezone.utc)
    family_id = uuid.uuid4()
    refresh_session, refresh_token = _new_refresh_session(user.id, family_id)
    session.add(refresh_session)
    await session.commit()
    await session.refresh(user)
    access_token, expires_in = create_access_token(user.id)
    return user, access_token, expires_in, refresh_token


async def rotate_refresh_token(session: AsyncSession, token: str) -> tuple[str, int, str]:
    now = datetime.now(timezone.utc)
    current = await session.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == _token_hash(token))
        .with_for_update()
    )
    if current is None:
        await session.rollback()
        raise AuthenticationError

    if current.rotated_at is not None:
        await session.execute(
            update(RefreshSession)
            .where(RefreshSession.family_id == current.family_id)
            .values(revoked_at=now)
        )
        # Commit before signaling replay so the dependency cleanup cannot undo revocation.
        await session.commit()
        raise AuthenticationError

    if current.revoked_at is not None or current.expires_at <= now:
        if current.revoked_at is None:
            current.revoked_at = now
            await session.commit()
        else:
            await session.rollback()
        raise AuthenticationError

    user = await session.scalar(select(User).where(User.id == current.user_id))
    if user is None or not user.is_active:
        current.revoked_at = now
        await session.commit()
        raise AuthenticationError

    replacement, replacement_token = _new_refresh_session(user.id, current.family_id)
    session.add(replacement)
    await session.flush()
    current.rotated_at = now
    current.replaced_by_id = replacement.id
    await session.commit()
    access_token, expires_in = create_access_token(user.id)
    return access_token, expires_in, replacement_token


async def revoke_refresh_token(session: AsyncSession, token: str | None) -> None:
    if not token:
        return
    current = await session.scalar(
        select(RefreshSession)
        .where(RefreshSession.token_hash == _token_hash(token))
        .with_for_update()
    )
    if current is not None and current.revoked_at is None:
        current.revoked_at = datetime.now(timezone.utc)
    await session.commit()


async def revoke_all_refresh_tokens(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(RefreshSession)
        .where(RefreshSession.user_id == user_id, RefreshSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await session.commit()


async def register_user(session: AsyncSession, payload: RegisterRequest) -> User:
    password_hash = await asyncio.to_thread(
        hash_password,
        payload.password.get_secret_value(),
    )

    user = User(
        username=payload.username,
        email=str(payload.email),
        password_hash=password_hash,
    )
    session.add(user)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise RegistrationConflictError from None

    await session.refresh(user)
    return user
