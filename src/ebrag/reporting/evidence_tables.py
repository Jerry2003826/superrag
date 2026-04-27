from __future__ import annotations

import csv
from io import StringIO

from ebrag.schemas.evidence import EvidenceSpan
from ebrag.schemas.extraction import ResultNode


def evidence_table_rows(
    *, results: list[ResultNode], evidence_spans: list[EvidenceSpan]
) -> list[dict[str, str]]:
    spans_by_id = {span.evidence_span_id: span for span in evidence_spans}
    rows: list[dict[str, str]] = []
    for result in results:
        span = spans_by_id.get(result.evidence_span_id)
        rows.append(
            {
                "result_id": result.result_id,
                "paper_id": result.paper_id,
                "study_id": result.study_id,
                "evidence_span_id": result.evidence_span_id,
                "scope": result.scope,
                "outcome": result.outcome,
                "direction": result.direction,
                "intervention": result.intervention or "",
                "section": span.section if span is not None and span.section is not None else "",
                "page": str(span.page) if span is not None and span.page is not None else "",
                "evidence_text": span.text if span is not None else "",
            }
        )
    return rows


def evidence_table_csv(*, results: list[ResultNode], evidence_spans: list[EvidenceSpan]) -> str:
    rows = evidence_table_rows(results=results, evidence_spans=evidence_spans)
    output = StringIO()
    fieldnames = [
        "result_id",
        "paper_id",
        "study_id",
        "evidence_span_id",
        "scope",
        "outcome",
        "direction",
        "intervention",
        "section",
        "page",
        "evidence_text",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()
