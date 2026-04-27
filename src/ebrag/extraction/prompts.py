from __future__ import annotations


def build_single_paper_extraction_prompt(*, paper_id: str, paper_context: str) -> str:
    return (
        "Extract biomedical result nodes from one paper only.\n"
        "Return only JSON matching this shape exactly:\n"
        "{\n"
        '  "paper_id": "P00000001",\n'
        '  "extraction_status": "unverified",\n'
        '  "results": [\n'
        "    {\n"
        '      "result_id": "R00000001",\n'
        '      "study_id": "S00000001",\n'
        '      "paper_id": "P00000001",\n'
        '      "study_type": "animal",\n'
        '      "intervention": "Compound X",\n'
        '      "outcome": "IL-6",\n'
        '      "direction": "decreased",\n'
        '      "scope": "animal",\n'
        '      "evidence_span_id": "E00000001",\n'
        '      "extraction_status": "unverified"\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Allowed direction values: increased, decreased, no_significant_difference, "
        "mixed, not_reported, unclear.\n"
        "Allowed scope values: in_vitro, animal, observational_human, clinical_trial, other.\n"
        "Use the study_id shown beside the cited evidence span.\n"
        "Every result must cite exactly one evidence_span_id from the evidence below.\n"
        "Do not infer numeric values that are absent from the evidence text.\n\n"
        f"paper_id: {paper_id}\n\n"
        f"evidence:\n{paper_context}"
    )
