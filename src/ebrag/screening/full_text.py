from __future__ import annotations


def build_full_text_screening_prompt(
    *,
    review_question: str,
    inclusion_criteria: list[str],
    exclusion_criteria: list[str],
    full_text_excerpt: str,
) -> str:
    include = "\n".join(f"- {item}" for item in inclusion_criteria)
    exclude = "\n".join(f"- {item}" for item in exclusion_criteria)
    return (
        "You are screening a biomedical paper for a systematic review.\n"
        f"Review question:\n{review_question}\n\n"
        f"Inclusion criteria:\n{include}\n\n"
        f"Exclusion criteria:\n{exclude}\n\n"
        "Return JSON with decision include/exclude/uncertain, reason_code, reason_text, "
        "and cited evidence_span_id when available.\n\n"
        f"Full text excerpt:\n{full_text_excerpt}"
    )
