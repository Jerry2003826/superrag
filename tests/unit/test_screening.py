from __future__ import annotations

from sqlalchemy.orm import Session

from ebrag.db.repositories import PaperRepository, ScreeningRepository
from ebrag.ingestion.dedup import normalize_title
from ebrag.reporting.prisma import build_prisma_counts
from ebrag.schemas.screening import ScreeningDecision
from ebrag.screening.full_text import build_full_text_screening_prompt
from ebrag.screening.stopping import should_stop_active_learning, uncertain_rate
from ebrag.screening.title_abstract import TitleAbstractScreeningBaseline


def test_title_abstract_baseline_include_exclude_uncertain() -> None:
    baseline = TitleAbstractScreeningBaseline(
        include_keywords=("compound x", "il-6", "mouse"),
        exclude_keywords=("review",),
    )

    included = baseline.screen(
        paper_id="P00000001",
        title="Compound X reduces IL-6",
        abstract="Mouse model experiment.",
    )
    excluded = baseline.screen(
        paper_id="P00000002",
        title="Narrative review of cytokines",
        abstract=None,
    )
    uncertain = baseline.screen(
        paper_id="P00000003",
        title="Unrelated biomarker",
        abstract=None,
    )

    assert included.decision == "include"
    assert excluded.decision == "exclude"
    assert uncertain.decision == "uncertain"


def test_full_text_prompt_contains_criteria_and_json_instruction() -> None:
    prompt = build_full_text_screening_prompt(
        review_question="Does compound X reduce IL-6 in AD mouse models?",
        inclusion_criteria=["Animal AD model", "Reports IL-6"],
        exclusion_criteria=["Review article"],
        full_text_excerpt="Evidence span E00000001 says IL-6 decreased.",
    )

    assert "Return JSON" in prompt
    assert "Animal AD model" in prompt
    assert "Evidence span E00000001" in prompt


def test_stopping_rule_and_prisma_counts() -> None:
    decisions = [
        ScreeningDecision(
            paper_id="P00000001",
            level="title_abstract",
            decision="include",
            reviewer_type="rule_based",
            confidence=0.9,
        ),
        ScreeningDecision(
            paper_id="P00000002",
            level="title_abstract",
            decision="exclude",
            reviewer_type="rule_based",
            confidence=0.9,
        ),
        ScreeningDecision(
            paper_id="P00000003",
            level="full_text",
            decision="uncertain",
            reviewer_type="llm",
            confidence=0.4,
        ),
    ]

    counts = build_prisma_counts(decisions)

    assert uncertain_rate(decisions) == 1 / 3
    assert not should_stop_active_learning(decisions, min_reviewed=3, max_uncertain_rate=0.05)
    assert counts.title_abstract_screened == 2
    assert counts.full_text_uncertain == 1


def test_screening_decision_repository_persists_audit(db_session: Session) -> None:
    paper = PaperRepository(db_session).create(
        title="Compound X mouse study",
        normalized_title=normalize_title("Compound X mouse study"),
    )

    decision = ScreeningRepository(db_session).create_decision(
        paper_id=paper.paper_id,
        level="title_abstract",
        decision="include",
        reason_code="include_keyword",
        reviewer_type="rule_based",
        confidence=0.8,
    )

    assert decision.decision_id == "D00000001"
