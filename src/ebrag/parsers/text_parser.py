from __future__ import annotations

from dataclasses import dataclass

from ebrag.parsers.base import read_source_bytes, source_hash, stable_id
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.paper import SourceDocument
from ebrag.schemas.parsing import ParsedChunk, ParsedDocument


@dataclass(frozen=True)
class TextParser:
    name: str = "text"
    version: str = "0.1"

    def can_parse(self, source: SourceDocument) -> bool:
        filename = source.filename or source.uri
        return source.source_format == "TEXT" or filename.lower().endswith(".txt")

    def parse(self, source: SourceDocument) -> ParsedDocument:
        data = read_source_bytes(source)
        text = data.decode("utf-8").strip()
        digest = source_hash(data)
        chunks = [
            ParsedChunk(
                chunk_id=stable_id("C", 1),
                paper_id=source.paper_id,
                section="Body",
                chunk_type="body",
                text=text,
                token_count=len(text.split()),
                source_format="TEXT",
                metadata={"parser": self.name},
            )
        ] if text else []
        evidence = [
            EvidenceSpan(
                evidence_span_id=stable_id("E", 1),
                paper_id=source.paper_id,
                source_format="TEXT",
                parser_name=self.name,
                parser_version=self.version,
                section="Body",
                paragraph=1,
                text=text,
                parse_confidence=0.9,
                source_hash=digest,
            )
        ] if text else []
        return ParsedDocument(
            parsed_id=stable_id("PD", 1),
            paper_id=source.paper_id,
            source_format="TEXT",
            parser_name=self.name,
            parser_version=self.version,
            object_uri=source.uri,
            parse_status="parsed" if text else "failed",
            parse_confidence=0.9 if text else 0.0,
            chunks=chunks,
            evidence_candidate_spans=evidence,
            source_hash=digest,
            error=None if text else "empty text document",
        )
