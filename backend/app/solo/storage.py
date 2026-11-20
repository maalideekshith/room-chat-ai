import asyncio
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.core.config import settings


class FileStorage(Protocol):
    async def put(self, owner_id: UUID, source_id: UUID, suffix: str, data: bytes) -> str: ...
    async def delete(self, key: str) -> None: ...


class LocalFileStorage:
    """Private local development storage; the API never returns its filesystem path."""

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.solo_storage_path).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("Invalid storage key")
        return path

    async def put(self, owner_id: UUID, source_id: UUID, suffix: str, data: bytes) -> str:
        key = f"{owner_id}/{source_id}{suffix}"
        path = self._path(key)

        def write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await asyncio.to_thread(write)
        return key

    async def delete(self, key: str) -> None:
        path = self._path(key)

        def remove() -> None:
            path.unlink(missing_ok=True)
            if path.parent != self.root:
                try:
                    path.parent.rmdir()
                except OSError:
                    # The owner's directory may still contain other stored sources.
                    pass

        await asyncio.to_thread(remove)
