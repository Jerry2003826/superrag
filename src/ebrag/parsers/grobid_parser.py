from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx
from lxml import etree

from ebrag.parsers.base import read_source_bytes, source_hash, stable_id
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.paper import SourceDocument
from ebrag.schemas.parsing import ChunkType, ParsedChunk, ParsedDocument

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def _tei_text(element: etree._Element | None) -> str:
    if element is None:
        return ""
    parts: list[str] = []
    for text in element.itertext():
        text_value = text.decode("utf-8") if isinstance(text, bytes) else text
        stripped = text_value.strip()
        if stripped:
            parts.append(stripped)
    return " ".join(parts)


def _elements(root: etree._Element, expression: str) -> list[etree._Element]:
    result = cast(list[Any], root.xpath(expression, namespaces=TEI_NS))
    return [item for item in result if isinstance(item, etree._Element)]


@dataclass(frozen=True)
class GrobidParser:
    grobid_url: str = "http://localhost:8070"
    timeout_seconds: float = 60.0
    name: str = "grobid"
    version: str = "0.8.0"

    def can_parse(self, source: SourceDocument) -> bool:
        filename = source.filename or source.uri
        return source.source_format == "PDF" or filename.lower().endswith(".pdf")

    def parse(self, source: SourceDocument) -> ParsedDocument:
        data = read_source_bytes(source)
        digest = source_hash(data)
        try:
            response = httpx.post(
                f"{self.grobid_url.rstrip('/')}/api/processFulltextDocument",
                files={"input": (source.filename or "paper.pdf", data, "application/pdf")},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            return self._parse_tei(source=source, tei_xml=response.content, digest=digest)
        except Exception as exc:
            return ParsedDocument(
                parsed_id=stable_id("PD", 1),
                paper_id=source.paper_id,
                source_format="PDF",
                parser_name=self.name,
                parser_version=self.version,
                object_uri=source.uri,
                parse_status="failed",
                parse_confidence=0.0,
                chunks=[],
                evidence_candidate_spans=[],
                references=[],
                source_hash=digest,
                error=str(exc),
            )

    def _parse_tei(self, *, source: SourceDocument, tei_xml: bytes, digest: str) -> ParsedDocument:
        root = etree.fromstring(tei_xml)
        title_el = _elements(root, ".//tei:titleStmt/tei:title")
        title = _tei_text(title_el[0]) if title_el else None
        abstract_el = _elements(root, ".//tei:profileDesc/tei:abstract")
        abstract = _tei_text(abstract_el[0]) if abstract_el else None
        chunks: list[ParsedChunk] = []
        references: list[str] = []

        def add_chunk(section: str | None, chunk_type: ChunkType, text: str) -> None:
            if not text.strip():
                return
            chunks.append(
                ParsedChunk(
                    chunk_id=stable_id("C", len(chunks) + 1),
                    paper_id=source.paper_id,
                    section=section,
                    chunk_type=chunk_type,
                    text=text.strip(),
                    token_count=len(text.split()),
                    source_format="PDF",
                    metadata={"parser": self.name},
                )
            )

        if title is not None:
            add_chunk("Title", "title", title)
        if abstract is not None:
            add_chunk("Abstract", "abstract", abstract)

        for div in _elements(root, ".//tei:text/tei:body//tei:div"):
            head = _elements(div, "./tei:head")
            section = _tei_text(head[0]) if head else "Body"
            for paragraph in _elements(div, "./tei:p"):
                add_chunk(section, "body", _tei_text(paragraph))

        for figure in _elements(root, ".//tei:figure"):
            fig_desc = _elements(figure, "./tei:figDesc")
            add_chunk("Figure", "figure_caption", _tei_text(fig_desc[0]) if fig_desc else "")

        for ref in _elements(root, ".//tei:listBibl//tei:biblStruct"):
            text = _tei_text(ref)
            if text:
                references.append(text)
                add_chunk("References", "reference", text)

        evidence_spans = [
            EvidenceSpan(
                evidence_span_id=stable_id("E", index),
                paper_id=source.paper_id,
                source_format="PDF",
                parser_name=self.name,
                parser_version=self.version,
                section=chunk.section,
                paragraph=index,
                text=chunk.text,
                parse_confidence=0.85,
                source_hash=digest,
            )
            for index, chunk in enumerate(chunks, start=1)
        ]
        return ParsedDocument(
            parsed_id=stable_id("PD", 1),
            paper_id=source.paper_id,
            source_format="PDF",
            parser_name=self.name,
            parser_version=self.version,
            object_uri=source.uri,
            parse_status="parsed",
            parse_confidence=0.85,
            title=title,
            abstract=abstract,
            chunks=chunks,
            evidence_candidate_spans=evidence_spans,
            references=references,
            source_hash=digest,
        )
