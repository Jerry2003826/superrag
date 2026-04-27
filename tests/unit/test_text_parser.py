from __future__ import annotations

from ebrag.parsers.text_parser import TextParser
from ebrag.schemas.paper import SourceDocument


def test_text_parser_turns_plain_text_into_chunk_and_evidence_span() -> None:
    parsed = TextParser().parse(
        SourceDocument(
            document_id="doc-1",
            paper_id="P00000001",
            source_format="TEXT",
            uri="memory://doc.txt",
            filename="doc.txt",
            content_bytes=b"Compound X reduced IL-6 in treated mice.",
        )
    )

    assert parsed.parse_status == "parsed"
    assert parsed.chunks[0].chunk_type == "body"
    assert parsed.evidence_candidate_spans[0].text == "Compound X reduced IL-6 in treated mice."
