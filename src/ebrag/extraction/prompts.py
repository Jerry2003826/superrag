from __future__ import annotations


def build_single_paper_extraction_prompt(*, paper_id: str, paper_context: str) -> str:
    return (
        "Extract biomedical result nodes from one paper only.\n"
        "Return JSON matching ExtractionOutput. Every result must cite an evidence_span_id.\n"
        "Do not infer numeric values that are absent from the evidence text.\n\n"
        f"paper_id: {paper_id}\n\n"
        f"evidence:\n{paper_context}"
    )
