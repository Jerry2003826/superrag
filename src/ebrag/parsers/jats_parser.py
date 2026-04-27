from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from lxml import etree

from ebrag.parsers.base import read_source_bytes, source_hash, stable_id
from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.paper import SourceDocument
from ebrag.schemas.parsing import ChunkType, ParsedChunk, ParsedDocument


def _text_content(element: etree._Element | None) -> str:
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
    result = cast(list[Any], root.xpath(expression))
    return [item for item in result if isinstance(item, etree._Element)]


def _xpath_first(root: etree._Element, expression: str) -> etree._Element | None:
    elements = _elements(root, expression)
    return elements[0] if elements else None


@dataclass(frozen=True)
class JATSParser:
    name: str = "jats"
    version: str = "0.1"

    def can_parse(self, source: SourceDocument) -> bool:
        filename = source.filename or source.uri
        return source.source_format == "JATS_XML" or filename.lower().endswith(".xml")

    def parse(self, source: SourceDocument) -> ParsedDocument:
        data = read_source_bytes(source)
        digest = source_hash(data)
        root = etree.fromstring(data)
        title = _text_content(_xpath_first(root, ".//article-title")) or None
        abstract = _text_content(_xpath_first(root, ".//abstract")) or None

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
                    source_format="JATS_XML",
                    metadata={},
                )
            )

        if title is not None:
            add_chunk("Title", "title", title)
        if abstract is not None:
            add_chunk("Abstract", "abstract", abstract)

        for sec in _elements(root, ".//body//sec"):
            section_title = _text_content(_xpath_first(sec, "./title")) or "Body"
            for paragraph in _elements(sec, "./p"):
                add_chunk(section_title, "body", _text_content(paragraph))

        for ref in _elements(root, ".//ref-list//ref"):
            text = _text_content(ref)
            if text:
                references.append(text)
                add_chunk("References", "reference", text)

        for fig in _elements(root, ".//fig"):
            label = _text_content(_xpath_first(fig, "./label"))
            caption = _text_content(_xpath_first(fig, "./caption"))
            add_chunk(label or "Figure", "figure_caption", caption)

        for table in _elements(root, ".//table-wrap"):
            label = _text_content(_xpath_first(table, "./label"))
            caption = _text_content(_xpath_first(table, "./caption"))
            add_chunk(label or "Table", "table_caption", caption)

        evidence_spans = [
            EvidenceSpan(
                evidence_span_id=stable_id("E", index),
                paper_id=source.paper_id,
                source_format="JATS_XML",
                parser_name=self.name,
                parser_version=self.version,
                section=chunk.section,
                page=None,
                paragraph=index,
                text=chunk.text,
                parse_confidence=0.95,
                source_hash=digest,
            )
            for index, chunk in enumerate(chunks, start=1)
        ]

        return ParsedDocument(
            parsed_id=stable_id("PD", 1),
            paper_id=source.paper_id,
            source_format="JATS_XML",
            parser_name=self.name,
            parser_version=self.version,
            object_uri=source.uri,
            parse_status="parsed",
            parse_confidence=0.95,
            title=title,
            abstract=abstract,
            chunks=chunks,
            evidence_candidate_spans=evidence_spans,
            references=references,
            source_hash=digest,
        )
