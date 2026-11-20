from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db_session
from app.schemas.auth import RegisterRequest, UserResponse
from app.services.auth import RegistrationConflictError, register_user

router = APIRouter(prefix=f"{settings.api_v1_prefix}/auth", tags=["auth"])


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
