from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.db.models import RiskFeedback, ReviewCase


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


def build_review_case(
    prediction: dict[str, Any],
    data: dict[str, Any],
) -> ReviewCase:
    """
    Build (but do NOT add/commit) a ReviewCase ORM object.

    Use this in bulk/batch flows where many cases are created in one
    request — the caller is responsible for db.add_all(...) and a
    single db.commit() across the whole batch (or in chunks), instead
    of one commit per case as create_review_case() does.

    Sets prediction['review_case_id'] in place, same as
    create_review_case() does, so downstream code (e.g. building the
    matching RiskFeedback row) can rely on it being present.
    """

    case_id = f"RG-{uuid4().hex[:10].upper()}"

    prediction["review_case_id"] = case_id

    return ReviewCase(
        case_id=case_id,
        status="OPEN",
        prediction=prediction,
        data=data,
    )


def list_review_cases(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
) -> dict[str, Any]:
    """
    Return a page of OPEN review cases, ordered oldest-first, with
    pagination metadata. If `search` is provided, filters case_id
    with a case-insensitive partial match (e.g. "F7D3" matches
    "RG-F7D32B73A7").
    """

    query = db.query(ReviewCase).filter(ReviewCase.status == "OPEN")

    if search:
        trimmed = search.strip()

        if trimmed:
            query = query.filter(
                ReviewCase.case_id.ilike(f"%{trimmed}%")
            )

    total = query.count()

    total_pages = max(1, (total + page_size - 1) // page_size)

    # Clamp so an out-of-range page (e.g. requesting page 9 after a
    # search narrows the results) doesn't return an empty page by
    # accident — it snaps back to the last valid page instead.
    page = max(1, min(page, total_pages))

    cases = (
        query
        .order_by(ReviewCase.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "cases": [
            _serialize_review_case(case)
            for case in cases
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


def list_review_analysis(
    db: Session,
    filter_type: str = "all",
    page: int = 1,
    page_size: int = 10,
    search: str | None = None,
) -> dict[str, Any]:
    """
    Return paginated RiskFeedback records for the Review Analysis
    dashboard.

    Filters:
    - all: every prediction
    - pending: predictions linked to an OPEN ReviewCase
    - allowed: model decision ALLOW
    - blocked: model decision BLOCK

    Search performs a case-insensitive partial match on case_id.
    """

    filter_type = filter_type.lower().strip()

    if filter_type not in {
        "all",
        "pending",
        "allowed",
        "blocked",
    }:
        raise ValueError(
            "filter_type must be one of: all, pending, allowed, blocked."
        )

    query = db.query(RiskFeedback)

    if filter_type == "allowed":
        query = query.filter(
            RiskFeedback.model_decision == "ALLOW"
        )

    elif filter_type == "blocked":
        query = query.filter(
            RiskFeedback.model_decision == "BLOCK"
        )

    elif filter_type == "pending":
        query = query.join(
            ReviewCase,
            ReviewCase.case_id == RiskFeedback.case_id,
        ).filter(
            ReviewCase.status == "OPEN"
        )

    if search:
        trimmed = search.strip()

        if trimmed:
            query = query.filter(
                RiskFeedback.case_id.ilike(
                    f"%{trimmed}%"
                )
            )

    total = query.count()

    total_pages = max(
        1,
        (total + page_size - 1) // page_size,
    )

    page = max(
        1,
        min(page, total_pages),
    )

    records = (
        query
        .order_by(RiskFeedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "records": [
            _serialize_feedback_record(record)
            for record in records
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


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


def _serialize_feedback_record(
    record: RiskFeedback,
) -> dict[str, Any]:
    return {
        "id": record.id,
        "case_id": record.case_id,
        "prediction": record.prediction,
        "predicted_label": record.predicted_label,
        "abuse_probability": record.abuse_probability,
        "risk_score": record.risk_score,
        "risk_level": record.risk_level,
        "model_decision": record.model_decision,
        "analyst_decision": record.analyst_decision,
        "actual_outcome": record.actual_outcome,
        "analyst_reason": record.analyst_reason,
        "input_data": record.input_data,
        "created_at": record.created_at.isoformat(),
        "outcome_recorded_at": (
            record.outcome_recorded_at.isoformat()
            if record.outcome_recorded_at
            else None
        ),
    }


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
