from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.db.models import Assignment, Assessment


def create_assignment(
    db: Session,
    assignment_number: str,
    assignment_name: str,
) -> Assignment:
    assignment_id = str(uuid4())

    assignment = Assignment(
        assignment_id=assignment_id,
        assignment_number=assignment_number.strip(),
        assignment_name=assignment_name.strip(),
        created_at=datetime.now(timezone.utc),
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


def get_assignment_by_number(
    db: Session,
    assignment_number: str,
) -> Assignment | None:
    return (
        db.query(Assignment)
        .filter(
            Assignment.assignment_number
            == assignment_number.strip()
        )
        .first()
    )


def get_assignment(
    db: Session,
    assignment_id: str,
) -> Assignment | None:
    return db.get(Assignment, assignment_id)


def create_assessment(
    db: Session,
    assignment_id: str,
    assessment_type: str,
    total_records: int,
) -> Assessment:
    assessment_id = f"RG-{uuid4().hex[:10].upper()}"

    assessment = Assessment(
        assessment_id=assessment_id,
        assignment_id=assignment_id,
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