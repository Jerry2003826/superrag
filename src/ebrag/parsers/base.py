from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Protocol

from ebrag.schemas.paper import SourceDocument
from ebrag.schemas.parsing import ParsedDocument


class ParserAdapter(Protocol):
    name: str
    version: str

    def can_parse(self, source: SourceDocument) -> bool:
        """Return whether this adapter can parse the source document."""

    def parse(self, source: SourceDocument) -> ParsedDocument:
        """Parse a source document into structured chunks and evidence spans."""


def read_source_bytes(source: SourceDocument) -> bytes:
    if source.content_bytes is not None:
        return source.content_bytes
    if source.local_path is not None:
        return source.local_path.read_bytes()
    path = Path(source.uri)
    if path.exists():
        return path.read_bytes()
    msg = f"Source has no readable content: {source.uri}"
    raise FileNotFoundError(msg)


def source_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(prefix: str, index: int) -> str:
    return f"{prefix}{index:08d}"
