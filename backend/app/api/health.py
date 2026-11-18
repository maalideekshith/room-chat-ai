from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.health import database_is_ready
from app.db.session import get_db_session

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/v1/health/db")
async def database_health(session: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    if await database_is_ready(session):
        return JSONResponse(status_code=200, content={"status": "ok", "database": "ok"})
    return JSONResponse(
        status_code=503,
        content={"status": "unavailable", "database": "unavailable"},
    )
