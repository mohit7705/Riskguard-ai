from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.db.models import ReviewCase


def create_review_case(
    db: Session,
    prediction: dict[str, Any],
    data: dict[str, Any],
) -> dict[str, Any]:
    case_id = f"RG-{uuid4().hex[:10].upper()}"

    prediction["review_case_id"] = case_id

    case = ReviewCase(
        case_id=case_id,
        status="OPEN",
        prediction=prediction,
        data=data,
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    return _serialize_review_case(case)


def list_review_cases(
    db: Session,
) -> list[dict[str, Any]]:
    cases = (
        db.query(ReviewCase)
        .filter(ReviewCase.status == "OPEN")
        .order_by(ReviewCase.created_at.asc())
        .all()
    )

    return [
        _serialize_review_case(case)
        for case in cases
    ]


def get_review_case(
    db: Session,
    case_id: str,
) -> dict[str, Any] | None:
    case = db.get(ReviewCase, case_id)

    if case is None:
        return None

    return _serialize_review_case(case)


def resolve_review_case(
    db: Session,
    case_id: str,
    decision: str,
    reason: str | None = None,
) -> dict[str, Any]:
    case = db.get(ReviewCase, case_id)

    if case is None:
        raise ValueError("Review case not found.")

    if case.status != "OPEN":
        raise ValueError("Review case is already resolved.")

    decision = decision.upper()

    if decision not in {"ALLOW", "BLOCK"}:
        raise ValueError(
            "Analyst decision must be ALLOW or BLOCK."
        )

    case.status = "RESOLVED"
    case.analyst_decision = decision
    case.analyst_reason = reason
    case.resolved_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(case)

    return _serialize_review_case(case)


def clear_review_cases(
    db: Session,
) -> None:
    db.query(ReviewCase).delete()
    db.commit()


def _serialize_review_case(
    case: ReviewCase,
) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "status": case.status,
        "created_at": case.created_at.isoformat(),
        "prediction": case.prediction,
        "data": case.data,
        "analyst_decision": case.analyst_decision,
        "analyst_reason": case.analyst_reason,
        "resolved_at": (
            case.resolved_at.isoformat()
            if case.resolved_at
            else None
        ),
    }
