from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ebrag.db import models
from ebrag.db.session import get_session

router = APIRouter(prefix="/review", tags=["review"])
SessionDep = Annotated[Session, Depends(get_session)]


@router.get("/queue")
def review_queue(session: SessionDep) -> list[dict[str, str | bool]]:
    reports = session.scalars(
        select(models.StudyReport).where(models.StudyReport.human_review_required.is_(True))
    )
    return [
        {
            "target_type": "study_report",
            "target_id": report.report_id,
            "paper_id": report.paper_id,
            "study_id": report.study_id,
            "human_review_required": report.human_review_required,
        }
        for report in reports
    ]
