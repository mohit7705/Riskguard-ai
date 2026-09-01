from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.db.models import Assessment


def create_assessment(
    db: Session,
    assessment_type: str,
    total_records: int,
) -> Assessment:
    assessment_id = f"RG-{uuid4().hex[:10].upper()}"

    assessment = Assessment(
        assessment_id=assessment_id,
        assessment_type=assessment_type.upper(),
        total_records=total_records,
        created_at=datetime.now(timezone.utc),
    )

    db.add(assessment)
    db.commit()
    db.refresh(assessment)

    return assessment


def get_assessment(
    db: Session,
    assessment_id: str,
) -> Assessment | None:
    return db.get(Assessment, assessment_id)