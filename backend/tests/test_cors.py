import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_cors_preflight_allows_configured_auth_request() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/auth/logout-all",
            headers={
                "Origin": settings.cors_origins[0],
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type,x-csrf-token",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == settings.cors_origins[0]
    assert response.headers["access-control-allow-credentials"] == "true"
    assert "POST" in response.headers["access-control-allow-methods"]
    allowed_headers = response.headers["access-control-allow-headers"].lower()
    assert {"authorization", "content-type", "x-csrf-token"} <= set(
        item.strip() for item in allowed_headers.split(",")
    )
    assert "*" not in response.headers["access-control-allow-methods"]
    assert "*" not in allowed_headers


@pytest.mark.asyncio
async def test_cors_preflight_allows_solo_resource_methods() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/solo/conversations/example",
            headers={
                "Origin": settings.cors_origins[0],
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,content-type,x-csrf-token",
            },
        )
    assert response.status_code == 200
    assert "PATCH" in response.headers["access-control-allow-methods"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("origin", "method", "requested_headers"),
    [
        ("https://untrusted.example", "POST", "x-csrf-token"),
        (None, "TRACE", "x-csrf-token"),
        (None, "POST", "x-unapproved-header"),
    ],
)
async def test_cors_preflight_rejects_unconfigured_origin_method_or_header(
    origin: str | None,
    method: str,
    requested_headers: str,
) -> None:
    selected_origin = origin or settings.cors_origins[0]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": selected_origin,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": requested_headers,
            },
        )

    assert response.status_code == 400
    if origin is not None:
        assert "access-control-allow-origin" not in response.headers
