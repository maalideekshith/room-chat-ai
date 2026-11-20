import asyncio
import hashlib
import ipaddress
import socket
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urlsplit

import httpx
from pypdf import PdfReader

from app.core.config import settings

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}
ALLOWED_MIME_TYPES = {"application/pdf", "text/plain", "text/markdown", "text/x-markdown"}


class IngestionFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def validate_file(filename: str, content_type: str | None, data: bytes) -> str:
    from pathlib import PurePath

    extension = PurePath(filename).suffix.lower()
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    if extension not in ALLOWED_EXTENSIONS or mime not in ALLOWED_MIME_TYPES:
        raise IngestionFailure("unsupported_file_type")
    if not data:
        raise IngestionFailure("empty_file")
    if len(data) > settings.solo_max_upload_bytes:
        raise IngestionFailure("file_too_large")
    if extension == ".pdf" and not data.startswith(b"%PDF-"):
        raise IngestionFailure("invalid_pdf")
    return extension


def extract_file_text(filename: str, data: bytes) -> str:
    from pathlib import PurePath

    extension = PurePath(filename).suffix.lower()
    try:
        if extension == ".pdf":
            reader = PdfReader(BytesIO(data), strict=True)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        else:
            text = data.decode("utf-8-sig")
    except Exception:
        raise IngestionFailure("text_extraction_failed") from None
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not cleaned:
        raise IngestionFailure("no_extractable_text")
    return cleaned[:2_000_000]


class _ReadableHtml(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg", "iframe"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "iframe"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth and data.strip():
            self.parts.append(data.strip())


async def _assert_public_host(host: str) -> None:
    if not host or host.lower() == "localhost":
        raise IngestionFailure("url_not_allowed")
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            host, None, type=socket.SOCK_STREAM
        )
    except OSError:
        raise IngestionFailure("url_unreachable") from None
    if not addresses:
        raise IngestionFailure("url_unreachable")
    for result in addresses:
        address = ipaddress.ip_address(result[4][0].split("%", 1)[0])
        if not address.is_global:
            raise IngestionFailure("url_not_allowed")


async def fetch_url_text(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise IngestionFailure("url_not_allowed")
    try:
        if parsed.port is not None and parsed.port not in {80, 443}:
            raise IngestionFailure("url_not_allowed")
    except ValueError:
        raise IngestionFailure("url_not_allowed") from None
    await _assert_public_host(parsed.hostname or "")
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            async with client.stream("GET", url, headers={"Accept": "text/html,text/plain"}) as response:
                if 300 <= response.status_code < 400:
                    raise IngestionFailure("url_redirect_not_allowed")
                if response.status_code >= 400:
                    raise IngestionFailure("url_fetch_failed")
                content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
                if content_type not in {"text/html", "text/plain"}:
                    raise IngestionFailure("unsupported_url_content")
                chunks = bytearray()
                async for block in response.aiter_bytes():
                    chunks.extend(block)
                    if len(chunks) > settings.solo_max_upload_bytes:
                        raise IngestionFailure("url_content_too_large")
    except IngestionFailure:
        raise
    except httpx.TimeoutException:
        raise IngestionFailure("url_timeout") from None
    except httpx.HTTPError:
        raise IngestionFailure("url_fetch_failed") from None
    try:
        body = bytes(chunks).decode("utf-8", errors="replace")
    except (UnboundLocalError, UnicodeError):
        raise IngestionFailure("url_fetch_failed") from None
    if content_type == "text/html":
        parser = _ReadableHtml()
        parser.feed(body)
        body = "\n".join(parser.parts)
    body = "\n".join(line.strip() for line in body.splitlines() if line.strip())
    if not body:
        raise IngestionFailure("no_extractable_text")
    return body[:2_000_000], hashlib.sha256(bytes(chunks)).hexdigest()


def chunk_text(text: str, size: int = 3_200, overlap: int = 400) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + size, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start + size // 2, end)
            if boundary > start:
                end = boundary
        chunks.append(normalized[start:end].strip())
        if end == len(normalized):
            break
        start = max(end - overlap, start + 1)
    return chunks
