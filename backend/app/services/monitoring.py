from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.db.models import RiskFeedback


def get_feedback_records(
    db: Session,
) -> list[RiskFeedback]:
    return (
        db.query(RiskFeedback)
        .order_by(RiskFeedback.created_at.desc())
        .all()
    )


def get_feedback_record(
    db: Session,
    feedback_id: int,
) -> RiskFeedback | None:
    return db.get(RiskFeedback, feedback_id)


def get_feedback_record_by_case_id(
    db: Session,
    case_id: str,
) -> RiskFeedback | None:
    return (
        db.query(RiskFeedback)
        .filter(RiskFeedback.case_id == case_id)
        .order_by(RiskFeedback.created_at.desc())
        .first()
    )


def calculate_monitoring_metrics(
    db: Session,
) -> dict:
    records = (
        db.query(RiskFeedback)
        .filter(RiskFeedback.actual_outcome.is_not(None))
        .all()
    )

    total_records = db.query(RiskFeedback).count()
    labeled_records = len(records)

    if labeled_records == 0:
        return {
            "total_records": total_records,
            "labeled_records": 0,
            "accuracy": None,
            "precision": None,
            "recall": None,
            "false_positive_count": 0,
            "false_negative_count": 0,
            "true_positive_count": 0,
            "true_negative_count": 0,
        }

    true_positive = 0
    true_negative = 0
    false_positive = 0
    false_negative = 0

    for record in records:
        predicted_abusive = record.predicted_label == 1
        actual_abusive = record.actual_outcome == "ABUSIVE"

        if predicted_abusive and actual_abusive:
            true_positive += 1
        elif not predicted_abusive and not actual_abusive:
            true_negative += 1
        elif predicted_abusive and not actual_abusive:
            false_positive += 1
        elif not predicted_abusive and actual_abusive:
            false_negative += 1

    accuracy = (
        (true_positive + true_negative) / labeled_records
    )

    precision_denominator = true_positive + false_positive
    recall_denominator = true_positive + false_negative

    precision = (
        true_positive / precision_denominator
        if precision_denominator
        else None
    )

    recall = (
        true_positive / recall_denominator
        if recall_denominator
        else None
    )

    return {
        "total_records": total_records,
        "labeled_records": labeled_records,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "false_positive_count": false_positive,
        "false_negative_count": false_negative,
        "true_positive_count": true_positive,
        "true_negative_count": true_negative,
    }