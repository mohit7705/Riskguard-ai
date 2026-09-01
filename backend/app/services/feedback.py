from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.db.models import RiskFeedback


def save_prediction_feedback(
    db: Session,
    prediction: dict[str, Any],
    data: dict[str, Any],
    assessment_id: str | None = None,
) -> RiskFeedback:
    feedback = RiskFeedback(
        assessment_id=assessment_id,
        case_id=prediction.get("review_case_id"),
        prediction=prediction["prediction"],
        predicted_label=prediction["predicted_label"],
        abuse_probability=prediction["abuse_probability"],
        risk_score=prediction["risk_score"],
        risk_level=prediction["risk_level"],
        model_decision=prediction["decision"],
        input_data=data,
    )

    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return feedback


def update_feedback_decision(
    db: Session,
    feedback_id: int,
    analyst_decision: str,
    analyst_reason: str | None = None,
) -> RiskFeedback:
    feedback = db.get(RiskFeedback, feedback_id)

    if feedback is None:
        raise ValueError("Feedback record not found.")

    decision = analyst_decision.upper()

    if decision not in {"ALLOW", "BLOCK"}:
        raise ValueError(
            "Analyst decision must be ALLOW or BLOCK."
        )

    feedback.analyst_decision = decision
    feedback.analyst_reason = analyst_reason

    db.commit()
    db.refresh(feedback)

    return feedback


def record_actual_outcome(
    db: Session,
    feedback_id: int,
    actual_outcome: str,
) -> RiskFeedback:
    feedback = db.get(RiskFeedback, feedback_id)

    if feedback is None:
        raise ValueError("Feedback record not found.")

    outcome = actual_outcome.upper()

    if outcome not in {"LEGITIMATE", "ABUSIVE"}:
        raise ValueError(
            "Actual outcome must be LEGITIMATE or ABUSIVE."
        )

    feedback.actual_outcome = outcome
    feedback.outcome_recorded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(feedback)

    return feedback
