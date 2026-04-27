from __future__ import annotations

from ebrag.schemas.retrieval import EvidencePack


def build_synthesis_prompt(pack: EvidencePack) -> str:
    evidence_lines = [
        f"- result_id={result.result_id}; evidence_span_id={result.evidence_span_id}; "
        f"scope={result.scope}; direction={result.direction}; outcome={result.outcome}"
        for result in pack.eligible_results
    ]
    span_lines = [
        f"- {span.evidence_span_id}: {span.text}" for span in pack.supporting_evidence
    ]
    return (
        "Write an evidence-grounded synthesis using only this EvidencePack.\n"
        "Every sentence must include cited_result_ids and cited_evidence_span_ids.\n"
        "Return JSON with a sentences list.\n\n"
        f"Query: {pack.query}\n"
        f"Sufficiency: {pack.sufficiency} ({pack.sufficiency_reason})\n\n"
        "Results:\n"
        + "\n".join(evidence_lines)
        + "\n\nEvidence spans:\n"
        + "\n".join(span_lines)
    )
