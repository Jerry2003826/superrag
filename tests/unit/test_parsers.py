from __future__ import annotations

from pathlib import Path

from ebrag.parsers.jats_parser import JATSParser
from ebrag.parsers.qc import run_parsing_qc
from ebrag.parsers.router import ParserRouter
from ebrag.schemas.paper import SourceDocument


def test_parser_router_selects_jats(sample_jats_path: Path) -> None:
    source = SourceDocument(
        document_id="doc-1",
        paper_id="P00000001",
        source_format="JATS_XML",
        uri=str(sample_jats_path),
        local_path=sample_jats_path,
    )

    router = ParserRouter(adapters=(JATSParser(),))

    assert router.route(source).name == "jats"


def test_jats_parser_extracts_chunks_evidence_and_qc(sample_jats_path: Path) -> None:
    source = SourceDocument(
        document_id="doc-1",
        paper_id="P00000001",
        source_format="JATS_XML",
        uri=str(sample_jats_path),
        local_path=sample_jats_path,
    )

    parsed = JATSParser().parse(source)
    qc_report = run_parsing_qc(parsed)

    assert parsed.parse_status == "parsed"
    assert parsed.title == "Compound X reduces IL-6 in AD mouse models"
    assert any(chunk.section == "Results" for chunk in parsed.chunks)
    assert any(chunk.chunk_type == "figure_caption" for chunk in parsed.chunks)
    assert len(parsed.evidence_candidate_spans) == len(parsed.chunks)
    assert all(span.source_format == "JATS_XML" for span in parsed.evidence_candidate_spans)
    assert qc_report.qc_status == "pass_with_warnings"
