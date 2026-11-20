import uuid
from datetime import datetime, timedelta, timezone

import jwt
from jwt.exceptions import InvalidTokenError
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

_password_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False


def create_access_token(subject: uuid.UUID) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    lifetime = settings.access_token_minutes * 60
    payload = {
        "sub": str(subject),
        "jti": str(uuid.uuid4()),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(seconds=lifetime),
    }
    assert settings.jwt_signing_secret is not None
    return jwt.encode(payload, settings.jwt_signing_secret, algorithm=settings.jwt_algorithm), lifetime


def decode_access_token(token: str) -> uuid.UUID:
    assert settings.jwt_signing_secret is not None
    payload = jwt.decode(
        token,
        settings.jwt_signing_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={"require": ["sub", "jti", "iss", "aud", "iat", "exp"]},
    )
    try:
        subject = uuid.UUID(payload["sub"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidTokenError("Invalid subject") from exc
    if str(subject) != payload["sub"]:
        raise InvalidTokenError("Subject must be a canonical UUID")
    try:
        uuid.UUID(payload["jti"])
    except (ValueError, TypeError, AttributeError) as exc:
        raise InvalidTokenError("Invalid JWT ID") from exc
    return subject
