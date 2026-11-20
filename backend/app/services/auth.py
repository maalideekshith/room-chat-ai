import asyncio

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import RegisterRequest


class RegistrationConflictError(Exception):
    pass


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
