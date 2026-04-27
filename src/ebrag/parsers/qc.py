from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from ebrag.schemas.ids import StableId
from ebrag.schemas.parsing import ParsedDocument


class ParsingQCReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: StableId
    title_ok: bool
    abstract_ok: bool
    section_headings_ok: bool
    methods_results_separated: bool
    tables_ok: Literal["yes", "partial", "no"]
    figure_legends_ok: bool
    page_mapping_ok: bool
    bbox_ok: bool
    qc_status: Literal["pass", "pass_with_warnings", "quarantine"]


def run_parsing_qc(parsed_document: ParsedDocument) -> ParsingQCReport:
    sections = {chunk.section for chunk in parsed_document.chunks if chunk.section}
    has_tables = any(chunk.chunk_type == "table_caption" for chunk in parsed_document.chunks)
    has_figures = any(chunk.chunk_type == "figure_caption" for chunk in parsed_document.chunks)
    page_mapping_ok = parsed_document.source_format == "JATS_XML" or any(
        chunk.page_start is not None for chunk in parsed_document.chunks
    )
    bbox_ok = any(span.bbox is not None for span in parsed_document.evidence_candidate_spans)
    title_ok = bool(parsed_document.title)
    abstract_ok = bool(parsed_document.abstract)
    section_headings_ok = bool(sections)
    methods_results_separated = "Methods" in sections and "Results" in sections
    qc_status: Literal["pass", "pass_with_warnings", "quarantine"] = "pass"
    if not title_ok or not abstract_ok or not section_headings_ok:
        qc_status = "quarantine"
    elif not page_mapping_ok or not bbox_ok or not methods_results_separated:
        qc_status = "pass_with_warnings"

    return ParsingQCReport(
        paper_id=parsed_document.paper_id,
        title_ok=title_ok,
        abstract_ok=abstract_ok,
        section_headings_ok=section_headings_ok,
        methods_results_separated=methods_results_separated,
        tables_ok="yes" if has_tables else "partial",
        figure_legends_ok=has_figures,
        page_mapping_ok=page_mapping_ok,
        bbox_ok=bbox_ok,
        qc_status=qc_status,
    )


def mark_quarantine_if_required(report: ParsingQCReport) -> bool:
    return report.qc_status == "quarantine"
