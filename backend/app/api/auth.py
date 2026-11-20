import secrets
from hmac import compare_digest

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import (
    AuthenticationError,
    RegistrationConflictError,
    login_user,
    register_user,
    revoke_all_refresh_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
)

router = APIRouter(prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"])
CSRF_HEADER_NAME = "X-CSRF-Token"


def _set_session_cookies(response: Response, refresh_token: str) -> str:
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        settings.refresh_cookie_name,
        refresh_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=settings.auth_cookie_path,
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        csrf_token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=False,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        path=settings.auth_cookie_path,
    )
    return csrf_token


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(
        settings.refresh_cookie_name,
        path=settings.auth_cookie_path,
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=settings.auth_cookie_samesite,
    )
    response.delete_cookie(
        settings.csrf_cookie_name,
        path=settings.auth_cookie_path,
        secure=settings.auth_cookie_secure,
        httponly=False,
        samesite=settings.auth_cookie_samesite,
    )


def _require_csrf(request_header: str | None, csrf_cookie: str | None) -> None:
    if (
        not request_header
        or not csrf_cookie
        or not compare_digest(request_header.encode("utf-8"), csrf_cookie.encode("utf-8"))
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    try:
        user = await register_user(session, payload)
    except RegistrationConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email is already registered",
        ) from None
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    try:
        _, access_token, expires_in, refresh_token = await login_user(session, payload)
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    csrf_token = _set_session_cookies(response, refresh_token)
    return TokenResponse(
        access_token=access_token,
        csrf_token=csrf_token,
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    csrf_header: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
    csrf_cookie: str | None = Cookie(default=None, alias=settings.csrf_cookie_name),
    refresh_cookie: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    session: AsyncSession = Depends(get_db_session),
) -> TokenResponse:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    _require_csrf(csrf_header, csrf_cookie)
    if not refresh_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh session",
        )
    try:
        access_token, expires_in, new_refresh_token = await rotate_refresh_token(session, refresh_cookie)
    except AuthenticationError:
        _clear_session_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh session",
        ) from None
    csrf_token = _set_session_cookies(response, new_refresh_token)
    return TokenResponse(
        access_token=access_token,
        csrf_token=csrf_token,
        expires_in=expires_in,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    csrf_header: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
    csrf_cookie: str | None = Cookie(default=None, alias=settings.csrf_cookie_name),
    refresh_cookie: str | None = Cookie(default=None, alias=settings.refresh_cookie_name),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    _require_csrf(csrf_header, csrf_cookie)
    await revoke_refresh_token(session, refresh_cookie)
    _clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    response: Response,
    csrf_header: str | None = Header(default=None, alias=CSRF_HEADER_NAME),
    csrf_cookie: str | None = Cookie(default=None, alias=settings.csrf_cookie_name),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    _require_csrf(csrf_header, csrf_cookie)
    await revoke_all_refresh_tokens(session, user.id)
    _clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
