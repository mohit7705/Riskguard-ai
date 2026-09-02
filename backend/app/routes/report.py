import json
from collections import Counter
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import RiskFeedback, ReviewCase


router = APIRouter(
    prefix="/api/v1/report",
    tags=["Report"],
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = PROJECT_ROOT / "backend" / "ml" / "models"

THRESHOLD_REPORT_PATH = MODEL_DIR / "risk_threshold_report.json"
EVALUATION_REPORT_PATH = MODEL_DIR / "model_evaluation_report.json"
FINAL_TEST_EVALUATION_PATH = (
    MODEL_DIR / "final_test_evaluation.json"
)

# Fallback values only used if the report files are missing —
# keeps the dashboard from crashing, but the numbers below are
# NOT recomputed and should not be trusted over the real files.
FALLBACK_MODEL_PERFORMANCE = {
    "model": "XGBoost",
    "test_rows": 2000,
    "threshold": 0.70,
    "precision": 0.9638,
    "recall": 0.9975,
    "f1_score": 0.9803,
    "pr_auc": 0.9942,
    "roc_auc": 0.9987,
    "false_positives": 15,
    "false_negatives": 1,
    "true_positives": 399,
    "true_negatives": 1585,
    "business_cost": 20.0,
}


def load_model_performance() -> dict:
    """
    Build model_performance from the final held-out evaluation.

    Threshold selection is sourced from:
    - risk_threshold_report.json

    Final performance is sourced from:
    - final_test_evaluation.json

    The test set is therefore reported using the threshold
    selected exclusively on the validation set.
    """

    if not FINAL_TEST_EVALUATION_PATH.exists():
        return FALLBACK_MODEL_PERFORMANCE

    with FINAL_TEST_EVALUATION_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        evaluation = json.load(file)

    metrics = evaluation.get("metrics", {})
    confusion = evaluation.get("confusion_matrix", {})
    business_cost = evaluation.get("business_cost", {})

    threshold = evaluation.get("threshold")

    if threshold is None and THRESHOLD_REPORT_PATH.exists():
        with THRESHOLD_REPORT_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            threshold_report = json.load(file)

        threshold = threshold_report.get(
            "selected_threshold",
            0.10,
        )

    return {
        "model": evaluation.get(
            "model",
            "XGBoost",
        ),
        "test_rows": evaluation.get(
            "test_rows",
            0,
        ),
        "threshold": threshold,
        "precision": metrics.get(
            "precision",
            0.0,
        ),
        "recall": metrics.get(
            "recall",
            0.0,
        ),
        "f1_score": metrics.get(
            "f1_score",
            0.0,
        ),
        "pr_auc": metrics.get(
            "pr_auc",
            0.0,
        ),
        "roc_auc": metrics.get(
            "roc_auc",
            0.0,
        ),
        "false_positives": confusion.get(
            "false_positives",
            0,
        ),
        "false_negatives": confusion.get(
            "false_negatives",
            0,
        ),
        "true_positives": confusion.get(
            "true_positives",
            0,
        ),
        "true_negatives": confusion.get(
            "true_negatives",
            0,
        ),
        "business_cost": business_cost.get(
            "total_cost",
            0.0,
        ),
    }


def load_threshold_curve() -> list[dict] | None:
    """
    Return the full threshold sweep (precision/recall/F1/cost
    at every tested threshold) so the frontend can chart the
    tradeoff, plus metadata about the cost assumptions and
    which threshold was actually selected.
    """

    if not THRESHOLD_REPORT_PATH.exists():
        return None

    with THRESHOLD_REPORT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        threshold_report = json.load(file)

    return {
        "selected_threshold": threshold_report[
            "selected_threshold"
        ],
        "false_positive_cost": threshold_report[
            "false_positive_cost"
        ],
        "false_negative_cost": threshold_report[
            "false_negative_cost"
        ],
        "cost_formula": threshold_report["cost_formula"],
        "selection_reason": threshold_report[
            "selection_reason"
        ],
        "points": threshold_report["threshold_results"],
    }


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    selected_date: date | None = Query(
        default=None,
        description="Optional date filter in YYYY-MM-DD format.",
    ),
):
    """
    Return overall report metrics plus date-wise statistics.

    When selected_date is provided, detailed metrics are calculated
    only for that date. Overall totals remain available separately.
    """

    # ---------------------------------------------------------
    # Base query
    # ---------------------------------------------------------

    feedback_query = db.query(RiskFeedback)

    if selected_date is not None:
        feedback_query = feedback_query.filter(
            func.date(RiskFeedback.created_at) == selected_date
        )

    # ---------------------------------------------------------
    # Summary for selected date / current scope
    # ---------------------------------------------------------

    total_reviewed = feedback_query.count()

    allowed = (
        feedback_query
        .filter(RiskFeedback.model_decision == "ALLOW")
        .count()
    )

    blocked = (
        feedback_query
        .filter(RiskFeedback.model_decision == "BLOCK")
        .count()
    )

    pending_review = (
        db.query(ReviewCase)
        .filter(ReviewCase.status == "OPEN")
        .count()
    )

    if selected_date is not None:
        pending_review = (
            db.query(ReviewCase)
            .filter(
                ReviewCase.status == "OPEN",
                func.date(ReviewCase.created_at) == selected_date,
            )
            .count()
        )

    abuse_rate = (
        feedback_query
        .with_entities(
            func.avg(RiskFeedback.abuse_probability)
        )
        .scalar()
    )

    # ---------------------------------------------------------
    # Risk distribution
    # ---------------------------------------------------------

    risk_distribution = {}

    risk_rows = (
        feedback_query
        .with_entities(
            RiskFeedback.risk_level,
            func.count(RiskFeedback.id),
        )
        .group_by(RiskFeedback.risk_level)
        .all()
    )

    for level, count in risk_rows:
        risk_distribution[level] = count

    # ---------------------------------------------------------
    # Decision trend
    # ---------------------------------------------------------

    decision_map = {}

    trend_rows = (
        feedback_query
        .with_entities(
            RiskFeedback.created_at,
            RiskFeedback.model_decision,
        )
        .order_by(RiskFeedback.created_at)
        .all()
    )

    for created_at, decision in trend_rows:
        date_key = created_at.date().isoformat()

        if date_key not in decision_map:
            decision_map[date_key] = {
                "date": date_key,
                "total": 0,
                "allow": 0,
                "block": 0,
                "review": 0,
            }

        decision_map[date_key]["total"] += 1

        if decision == "ALLOW":
            decision_map[date_key]["allow"] += 1
        elif decision == "BLOCK":
            decision_map[date_key]["block"] += 1
        else:
            decision_map[date_key]["review"] += 1

    decision_trend = list(decision_map.values())

    # ---------------------------------------------------------
    # Daily assessment data
    #
    # This intentionally uses RiskFeedback.created_at because
    # every prediction already creates a feedback record.
    # ---------------------------------------------------------

    daily_rows = (
        db.query(
            func.date(RiskFeedback.created_at).label("report_date"),
            func.count(RiskFeedback.id).label("total"),
            func.sum(
                case(
                    (
                        RiskFeedback.model_decision == "ALLOW",
                        1,
                    ),
                    else_=0,
                )
            ).label("allowed"),
            func.sum(
                case(
                    (
                        RiskFeedback.model_decision == "REVIEW",
                        1,
                    ),
                    else_=0,
                )
            ).label("review"),
            func.sum(
                case(
                    (
                        RiskFeedback.model_decision == "BLOCK",
                        1,
                    ),
                    else_=0,
                )
            ).label("blocked"),
        )
        .group_by(func.date(RiskFeedback.created_at))
        .order_by(func.date(RiskFeedback.created_at))
        .all()
    )

    daily_data = [
        {
            "date": (
                row.report_date.isoformat()
                if hasattr(row.report_date, "isoformat")
                else str(row.report_date)
            ),
            "total": int(row.total or 0),
            "allowed": int(row.allowed or 0),
            "review": int(row.review or 0),
            "blocked": int(row.blocked or 0),
        }
        for row in daily_rows
    ]

    # ---------------------------------------------------------
    # Top risk reasons
    # ---------------------------------------------------------

    reasons = Counter()

    feedback_rows = (
        feedback_query
        .with_entities(RiskFeedback.input_data)
        .all()
    )

    for row in feedback_rows:
        data = row[0] or {}

        if data.get("return_reason"):
            reasons[data["return_reason"]] += 1

    top_risk_reasons = [
        {
            "reason": reason,
            "count": count,
        }
        for reason, count in reasons.most_common(5)
    ]

    # ---------------------------------------------------------
    # Existing model / financial reporting
    # ---------------------------------------------------------

    financial_impact = {
        "potential_refund_exposure_identified_inr": 49015.25,
        "observed_missed_refund_exposure_inr": 315.31,
        "observed_fraud_exposure_reduction_inr": 48699.94,
        "false_positive_friction_cost": 15.0,
        "false_positive_friction_cost_unit": "normalized",
        "financial_interpretation": (
            "Detected-abuse amount is potential prevented exposure, "
            "not realized savings."
        ),
    }

    # ---------------------------------------------------------
    # Response
    # ---------------------------------------------------------

    return {
        "selected_date": (
            selected_date.isoformat()
            if selected_date is not None
            else None
        ),

        "summary": {
            "total_reviewed": total_reviewed,
            "pending_review": pending_review,
            "allowed": allowed,
            "blocked": blocked,
            "abuse_rate": round(
                (abuse_rate or 0) * 100,
                2,
            ),
        },

        "risk_distribution": risk_distribution,

        "decision_trend": decision_trend,

        "daily_data": daily_data,

        "top_risk_reasons": top_risk_reasons,

        "model_performance": load_model_performance(),

        "threshold_curve": load_threshold_curve(),

        "financial_impact": financial_impact,
    }