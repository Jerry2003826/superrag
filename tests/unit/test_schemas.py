from __future__ import annotations

import pytest
from pydantic import ValidationError

from ebrag.schemas.evidence import BoundingBox, EvidenceSpan
from ebrag.schemas.extraction import ResultNode
from ebrag.schemas.verification import VerificationVerdict


def test_evidence_span_requires_text_and_valid_ids() -> None:
    with pytest.raises(ValidationError):
        EvidenceSpan(
            evidence_span_id="bad",
            paper_id="P00000001",
            source_format="JATS_XML",
            parser_name="jats",
            text="",
        )


def test_bounding_box_requires_positive_area() -> None:
    with pytest.raises(ValidationError):
        BoundingBox(page=1, x1=10, y1=10, x2=5, y2=20)


def test_result_node_rejects_illegal_scope() -> None:
    with pytest.raises(ValidationError):
        ResultNode(
            result_id="R00000001",
            study_id="S00000001",
            paper_id="P00000001",
            study_type="animal",
            outcome="IL-6",
            direction="decreased",
            scope="human",
            evidence_span_id="E00000001",
        )


def test_verification_verdict_rejects_illegal_verdict() -> None:
    with pytest.raises(ValidationError):
        VerificationVerdict(
            claim_id="CLM00000001",
            verdict="maybe",
            reason="not a supported verdict",
        )
