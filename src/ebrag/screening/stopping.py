from __future__ import annotations

from ebrag.schemas.screening import ScreeningDecision


def uncertain_rate(decisions: list[ScreeningDecision]) -> float:
    if not decisions:
        return 1.0
    uncertain = sum(1 for decision in decisions if decision.decision == "uncertain")
    return uncertain / len(decisions)


def should_stop_active_learning(
    decisions: list[ScreeningDecision],
    *,
    min_reviewed: int = 200,
    max_uncertain_rate: float = 0.05,
) -> bool:
    return len(decisions) >= min_reviewed and uncertain_rate(decisions) <= max_uncertain_rate
