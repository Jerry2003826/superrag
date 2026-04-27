from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ObjectStore(Protocol):
    def put_bytes(self, bucket: str, key: str, data: bytes) -> str:
        """Store bytes and return a stable object URI."""

    def put_file(self, bucket: str, key: str, path: Path) -> str:
        """Store a local file and return a stable object URI."""

    def get_bytes(self, bucket: str, key: str) -> bytes:
        """Read object bytes."""

    def exists(self, bucket: str, key: str) -> bool:
        """Return whether an object exists."""
