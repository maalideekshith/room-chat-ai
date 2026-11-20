import asyncio
import hashlib
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.api.auth import _clear_session_cookies, _require_csrf, _set_session_cookies
from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, hash_password
from app.main import app
from app.models.refresh_session import RefreshSession
from app.models.user import User

PASSWORD = "correct horse battery staple"


def _assert_cookie_attributes(header: str, *, httponly: bool) -> None:
    lowered = header.lower()
    assert f"path={settings.auth_cookie_path.lower()}" in lowered
    assert f"samesite={settings.auth_cookie_samesite}" in lowered
    assert ("; secure" in lowered) is settings.auth_cookie_secure
    assert ("; httponly" in lowered) is httponly


def test_refresh_and_csrf_cookie_attributes_and_clearing_match_settings() -> None:
    response = Response()
    _set_session_cookies(response, "opaque-refresh-token")
    set_headers = response.headers.getlist("set-cookie")
    refresh = next(
        item for item in set_headers if item.startswith(f"{settings.refresh_cookie_name}=")
    )
    csrf = next(
        item for item in set_headers if item.startswith(f"{settings.csrf_cookie_name}=")
    )
    _assert_cookie_attributes(refresh, httponly=True)
    _assert_cookie_attributes(csrf, httponly=False)

    cleared = Response()
    _clear_session_cookies(cleared)
    clear_headers = cleared.headers.getlist("set-cookie")
    refresh_clear = next(
        item for item in clear_headers if item.startswith(f"{settings.refresh_cookie_name}=")
    )
    csrf_clear = next(
        item for item in clear_headers if item.startswith(f"{settings.csrf_cookie_name}=")
    )
    assert "max-age=0" in refresh_clear.lower()
    assert "max-age=0" in csrf_clear.lower()
    _assert_cookie_attributes(refresh_clear, httponly=True)
    _assert_cookie_attributes(csrf_clear, httponly=False)


async def _make_user(session, *, active: bool = True) -> User:
    user = User(
        username="session_user",
        email="session@example.com",
        password_hash=await asyncio.to_thread(hash_password, PASSWORD),
        is_active=active,
    )
    session.add(user)
    await session.flush()
    return user


async def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_login_sets_access_token_and_securely_scoped_cookies(test_app_db_session) -> None:
    await _make_user(test_app_db_session)
    async with await _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": " SESSION_USER ", "password": PASSWORD},
        )

    assert response.status_code == 200
    body = response.json()
    cookie_headers = response.headers.get_list("set-cookie")
    assert set(body) == {"access_token", "csrf_token", "token_type", "expires_in"}
    assert body["csrf_token"] == next(
        value.split("=", 1)[1].split(";", 1)[0]
        for value in cookie_headers
        if value.startswith("csrf_token=")
    )
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.access_token_minutes * 60
    assert response.headers["cache-control"] == "no-store"
    refresh_header = next(
        value for value in cookie_headers if value.startswith(f"{settings.refresh_cookie_name}=")
    )
    csrf_header = next(
        value for value in cookie_headers if value.startswith(f"{settings.csrf_cookie_name}=")
    )
    _assert_cookie_attributes(refresh_header, httponly=True)
    _assert_cookie_attributes(csrf_header, httponly=False)


@pytest.mark.asyncio
async def test_login_accepts_email_and_rejects_bad_password_generically(test_app_db_session) -> None:
    await _make_user(test_app_db_session)
    async with await _client() as client:
        wrong = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "SESSION@example.com", "password": "wrong"},
        )
        missing = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "nobody", "password": "wrong"},
        )
    assert wrong.status_code == missing.status_code == 401
    assert wrong.json() == missing.json() == {"detail": "Invalid username/email or password"}


@pytest.mark.asyncio
async def test_login_rejects_inactive_user(test_app_db_session) -> None:
    await _make_user(test_app_db_session, active=False)
    async with await _client() as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "session_user", "password": PASSWORD},
        )
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username/email or password"}


def test_jwt_round_trip_and_rejects_invalid_claims_and_expiry() -> None:
    subject = uuid4()
    token, lifetime = create_access_token(subject)
    assert decode_access_token(token) == subject
    assert lifetime == settings.access_token_minutes * 60

    base = {
        "sub": str(subject), "jti": str(uuid4()), "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience, "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
    }
    for claims in (
        {**base, "iss": "wrong-issuer"},
        {**base, "aud": "wrong-audience"},
        {**base, "sub": "not-a-uuid"},
        {**base, "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        {**base, "iat": datetime.now(timezone.utc) + timedelta(minutes=1)},
        {key: value for key, value in base.items() if key != "jti"},
    ):
        bad_token = jwt.encode(claims, settings.jwt_signing_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(jwt.InvalidTokenError):
            decode_access_token(bad_token)

    wrong_algorithm = jwt.encode(base, settings.jwt_signing_secret, algorithm="HS512")
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(wrong_algorithm)


@pytest.mark.asyncio
async def test_refresh_rotates_and_replay_revokes_entire_family(test_app_db_session) -> None:
    await _make_user(test_app_db_session)
    async with await _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "session_user", "password": PASSWORD},
        )
        old_refresh = client.cookies.get(settings.refresh_cookie_name)
        csrf = client.cookies.get(settings.csrf_cookie_name)
        assert old_refresh and csrf
        refreshed = await client.post("/api/v1/auth/refresh", headers={"X-CSRF-Token": csrf})
        assert refreshed.status_code == 200
        replacement = client.cookies.get(settings.refresh_cookie_name)
        assert replacement and replacement != old_refresh
        family = await test_app_db_session.scalar(
            select(RefreshSession.family_id).where(RefreshSession.token_hash.is_not(None))
        )

        # The old credential is replayed with the current CSRF pair; reuse must commit revocation.
        csrf = client.cookies.get(settings.csrf_cookie_name)
        replay = await client.post(
            "/api/v1/auth/refresh",
            headers={"X-CSRF-Token": csrf},
            cookies={settings.refresh_cookie_name: old_refresh},
        )

    assert login.status_code == 200
    assert replay.status_code == 401
    rows = list((await test_app_db_session.scalars(
        select(RefreshSession).where(RefreshSession.family_id == family)
    )).all())
    assert len(rows) == 2
    assert all(row.revoked_at is not None for row in rows)


@pytest.mark.asyncio
async def test_logout_revokes_session_and_clears_cookies(test_app_db_session) -> None:
    await _make_user(test_app_db_session)
    async with await _client() as client:
        await client.post("/api/v1/auth/login", json={"username_or_email": "session_user", "password": PASSWORD})
        token_hash = hashlib.sha256(client.cookies.get(settings.refresh_cookie_name).encode()).hexdigest()
        csrf = client.cookies.get(settings.csrf_cookie_name)
        response = await client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 204
    stored = await test_app_db_session.scalar(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
    assert stored is not None and stored.revoked_at is not None
    clear_headers = response.headers.get_list("set-cookie")
    refresh_clear = next(
        item for item in clear_headers if item.startswith(f"{settings.refresh_cookie_name}=")
    )
    csrf_clear = next(
        item for item in clear_headers if item.startswith(f"{settings.csrf_cookie_name}=")
    )
    assert "max-age=0" in refresh_clear.lower()
    assert "max-age=0" in csrf_clear.lower()
    _assert_cookie_attributes(refresh_clear, httponly=True)
    _assert_cookie_attributes(csrf_clear, httponly=False)


@pytest.mark.asyncio
async def test_logout_all_requires_access_token_and_revokes_user_sessions(test_app_db_session) -> None:
    user = await _make_user(test_app_db_session)
    access_token, _ = create_access_token(user.id)
    async with await _client() as client:
        logged_in = await client.post("/api/v1/auth/login", json={"username_or_email": "session_user", "password": PASSWORD})
        csrf = client.cookies.get(settings.csrf_cookie_name)
        response = await client.post(
            "/api/v1/auth/logout-all",
            headers={"X-CSRF-Token": csrf, "Authorization": f"Bearer {access_token}"},
        )
        assert logged_in.status_code == 200
    assert response.status_code == 204
    sessions = list((await test_app_db_session.scalars(select(RefreshSession).where(RefreshSession.user_id == user.id))).all())
    assert sessions and all(item.revoked_at is not None for item in sessions)


def test_double_submit_csrf_requires_matching_nonempty_pair() -> None:
    _require_csrf("same-token", "same-token")
    for header, cookie in ((None, "x"), ("x", None), ("x", "y"), ("", "")):
        with pytest.raises(HTTPException) as exc:
            _require_csrf(header, cookie)
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_current_user_validates_token_and_active_status(test_app_db_session) -> None:
    user = await _make_user(test_app_db_session)
    token, _ = create_access_token(user.id)
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    loaded = await get_current_user(credentials, test_app_db_session)
    assert loaded.id == user.id

    user.is_active = False
    await test_app_db_session.flush()
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials, test_app_db_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_refresh_endpoint_enforces_csrf_before_session_validation() -> None:
    from app.db.session import get_db_session

    async def no_database_needed():
        yield object()

    app.dependency_overrides[get_db_session] = no_database_needed
    try:
        async with await _client() as client:
            client.cookies.set(settings.csrf_cookie_name, "cookie-value")
            rejected = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": "different-value"},
            )
            client.cookies.set(settings.csrf_cookie_name, "same-value")
            accepted = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": "same-value"},
            )
    finally:
        app.dependency_overrides.pop(get_db_session, None)
    assert rejected.status_code == 403
    assert accepted.status_code == 401  # CSRF passed; no refresh credential was supplied.


@pytest.mark.asyncio
async def test_current_user_rejects_invalid_bearer_token(test_app_db_session) -> None:
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-jwt")
    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials, test_app_db_session)
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_concurrent_refresh_allows_one_rotation_and_revokes_replay(test_app_database) -> None:
    user_id = uuid4()
    username = f"race_{user_id.hex[:12]}"
    factory = test_app_database
    async with factory() as session:
        user = User(
            id=user_id,
            username=username,
            email=f"{username}@example.com",
            password_hash=await asyncio.to_thread(hash_password, PASSWORD),
        )
        session.add(user)
        await session.commit()

    try:
        async with await _client() as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"username_or_email": username, "password": PASSWORD},
            )
        assert login.status_code == 200
        old_refresh = next(
            value.split("=", 1)[1].split(";", 1)[0]
            for value in login.headers.get_list("set-cookie")
            if value.startswith("refresh_token=")
        )
        csrf = login.json()["csrf_token"]

        async def send_refresh():
            async with await _client() as client:
                client.cookies.set(settings.refresh_cookie_name, old_refresh)
                client.cookies.set(settings.csrf_cookie_name, csrf)
                return await client.post(
                    "/api/v1/auth/refresh",
                    headers={"X-CSRF-Token": csrf},
                )

        first, second = await asyncio.gather(send_refresh(), send_refresh())
        assert sorted((first.status_code, second.status_code)) == [200, 401]
        async with factory() as session:
            sessions = list(
                (
                    await session.scalars(
                        select(RefreshSession).where(RefreshSession.user_id == user_id)
                    )
                ).all()
            )
        assert len(sessions) == 2
        assert all(item.revoked_at is not None for item in sessions)
    finally:
        async with factory() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "requires_bearer"),
    [("/api/v1/auth/logout", False), ("/api/v1/auth/logout-all", True)],
)
@pytest.mark.parametrize("csrf_header", [None, "mismatched-token"])
async def test_logout_routes_reject_bad_csrf_without_revoking_session(
    test_app_db_session,
    path: str,
    requires_bearer: bool,
    csrf_header: str | None,
) -> None:
    await _make_user(test_app_db_session)
    async with await _client() as client:
        login = await client.post(
            "/api/v1/auth/login",
            json={"username_or_email": "session_user", "password": PASSWORD},
        )
        refresh_token = client.cookies.get(settings.refresh_cookie_name)
        assert refresh_token
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        headers = {}
        if csrf_header is not None:
            headers["X-CSRF-Token"] = csrf_header
        if requires_bearer:
            headers["Authorization"] = f"Bearer {login.json()['access_token']}"
        response = await client.post(path, headers=headers)

    assert response.status_code == 403
    stored = await test_app_db_session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash)
    )
    assert stored is not None
    assert stored.revoked_at is None


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/v1/auth/logout", "/api/v1/auth/logout-all"])
@pytest.mark.parametrize("header", [None, "wrong-token"])
async def test_logout_csrf_rejection_precedes_any_revocation_operation(path, header) -> None:
    from app.api.auth import CSRF_HEADER_NAME
    from app.api.dependencies import get_current_user as current_user_dependency
    from app.db.session import get_db_session

    class SessionSpy:
        revocation_touched = False

        async def scalar(self, *args, **kwargs):
            self.revocation_touched = True

        async def execute(self, *args, **kwargs):
            self.revocation_touched = True

        async def commit(self):
            self.revocation_touched = True

    spy = SessionSpy()

    async def session_override():
        yield spy

    async def user_override():
        return User(
            id=uuid4(),
            username="csrf_user",
            email="csrf@example.com",
            password_hash="unused",
        )

    app.dependency_overrides[get_db_session] = session_override
    if path.endswith("logout-all"):
        app.dependency_overrides[current_user_dependency] = user_override
    try:
        async with await _client() as client:
            client.cookies.set(
                settings.refresh_cookie_name,
                "opaque-refresh-token",
                path=settings.auth_cookie_path,
            )
            client.cookies.set(
                settings.csrf_cookie_name,
                "csrf-cookie-token",
                path=settings.auth_cookie_path,
            )
            headers = {CSRF_HEADER_NAME: header} if header is not None else {}
            response = await client.post(path, headers=headers)
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        app.dependency_overrides.pop(current_user_dependency, None)

    assert response.status_code == 403
    assert spy.revocation_touched is False
