from __future__ import annotations

from dataclasses import dataclass

from ebrag.parsers.base import ParserAdapter
from ebrag.schemas.paper import SourceDocument
from ebrag.schemas.parsing import ParsedDocument


@dataclass(frozen=True)
class ParserRouter:
    adapters: tuple[ParserAdapter, ...]

    def route(self, source: SourceDocument) -> ParserAdapter:
        for adapter in self.adapters:
            if adapter.can_parse(source):
                return adapter
        msg = f"No parser adapter can parse {source.source_format} document {source.document_id}"
        raise ValueError(msg)

    def parse_with_fallbacks(self, source: SourceDocument) -> ParsedDocument:
        last_error: Exception | None = None
        for adapter in self.adapters:
            if not adapter.can_parse(source):
                continue
            try:
                parsed = adapter.parse(source)
            except Exception as exc:
                last_error = exc
                continue
            if parsed.parse_status != "failed":
                return parsed
            last_error = RuntimeError(parsed.error or f"{adapter.name} failed")

        if last_error is not None:
            raise last_error
        return self.route(source).parse(source)
