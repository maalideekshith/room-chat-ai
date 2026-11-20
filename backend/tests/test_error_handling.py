import logging

from starlette.requests import Request

from app.main import unhandled_exception_handler


async def test_unhandled_exception_is_logged_but_response_stays_generic(caplog) -> None:
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/unexpected",
            "raw_path": b"/unexpected",
            "query_string": b"",
            "headers": [],
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
        }
    )
    exception = RuntimeError("private token password database details")

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = await unhandled_exception_handler(request, exception)

    assert response.status_code == 500
    assert response.body == b'{"detail":"Internal server error"}'
    assert "Unhandled application exception" in caplog.text
    assert "private token password database details" not in response.body.decode()
