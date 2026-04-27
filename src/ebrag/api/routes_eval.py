from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from ebrag.evaluation.regression import run_regression
from ebrag.schemas.evaluation import EvaluationPrediction, GoldCase

router = APIRouter(prefix="/eval", tags=["evaluation"])


class EvalRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gold_cases: list[GoldCase] = Field(default_factory=list)
    predictions: list[EvaluationPrediction] = Field(default_factory=list)


@router.post("/run-gold")
def run_gold(request: EvalRunRequest) -> dict[str, object]:
    return run_regression(
        gold_cases=request.gold_cases,
        predictions=request.predictions,
    ).model_dump()
