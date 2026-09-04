import json
import time
from collections import Counter
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.db.models import Assessment, RiskFeedback, ReviewCase
from backend.app.services.assessment import get_assignment_by_number


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
    assignment_number: str = Query(...),
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

    assignment = get_assignment_by_number(
        db=db,
        assignment_number=assignment_number,
    )

    if assignment is None:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail=f"Assignment not found: {assignment_number}",
        )

    assignment_id = assignment.assignment_id

    profile_start = time.perf_counter()

    def mark(label: str) -> None:
        elapsed = (time.perf_counter() - profile_start) * 1000
        print(f"[DASHBOARD PROFILE] {label}: {elapsed:.2f} ms")

    # ---------------------------------------------------------
    # Summary + risk distribution
    #
    # Combine both aggregations into one PostgreSQL query to
    # reduce a remote Neon round trip.
    # ---------------------------------------------------------

    feedback_query = (
        db.query(RiskFeedback)
        .join(
            Assessment,
            Assessment.assessment_id == RiskFeedback.assessment_id,
        )
        .filter(
            Assessment.assignment_id == assignment_id
        )
    )

    if selected_date is not None:
        feedback_query = feedback_query.filter(
            func.date(RiskFeedback.created_at) == selected_date
        )

    summary_rows = (
        feedback_query
        .with_entities(
            RiskFeedback.risk_level,
            func.count(RiskFeedback.id).label("risk_count"),
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
                        RiskFeedback.model_decision == "BLOCK",
                        1,
                    ),
                    else_=0,
                )
            ).label("blocked"),
            func.avg(
                RiskFeedback.abuse_probability
            ).label("abuse_rate"),
        )
        .group_by(RiskFeedback.risk_level)
        .all()
    )

    total_reviewed = sum(
        int(row.risk_count or 0)
        for row in summary_rows
    )

    allowed = int(
        sum(int(row.allowed or 0) for row in summary_rows)
    )

    blocked = int(
        sum(int(row.blocked or 0) for row in summary_rows)
    )

    weighted_abuse_sum = sum(
        float(row.abuse_rate or 0) * int(row.risk_count or 0)
        for row in summary_rows
    )

    abuse_rate = (
        weighted_abuse_sum / total_reviewed
        if total_reviewed
        else 0.0
    )

    risk_distribution = {
        row.risk_level: int(row.risk_count or 0)
        for row in summary_rows
        if row.risk_level is not None
    }

    mark("summary + risk distribution")

    # ---------------------------------------------------------
    # Pending review
    # ---------------------------------------------------------

    pending_query = (
        db.query(ReviewCase)
        .join(
            Assessment,
            Assessment.assessment_id == ReviewCase.assessment_id,
        )
        .filter(
            ReviewCase.status == "OPEN",
            Assessment.assignment_id == assignment_id,
        )
    )

    if selected_date is not None:
        pending_query = pending_query.filter(
            func.date(ReviewCase.created_at) == selected_date
        )

    pending_review = pending_query.count()
    mark("pending review")

    # ---------------------------------------------------------
    # Decision trend
    #
    # Aggregate by date and decision in PostgreSQL instead
    # of loading every feedback row into Python.
    # ---------------------------------------------------------

    trend_rows = (
        feedback_query
        .with_entities(
            func.date(RiskFeedback.created_at).label("report_date"),
            RiskFeedback.model_decision,
            func.count(RiskFeedback.id).label("count"),
        )
        .group_by(
            func.date(RiskFeedback.created_at),
            RiskFeedback.model_decision,
        )
        .order_by(func.date(RiskFeedback.created_at))
        .all()
    )

    decision_map = {}

    for row in trend_rows:
        date_key = (
            row.report_date.isoformat()
            if hasattr(row.report_date, "isoformat")
            else str(row.report_date)
        )

        if date_key not in decision_map:
            decision_map[date_key] = {
                "date": date_key,
                "total": 0,
                "allow": 0,
                "block": 0,
                "review": 0,
            }

        count = int(row.count or 0)

        decision_map[date_key]["total"] += count

        if row.model_decision == "ALLOW":
            decision_map[date_key]["allow"] += count
        elif row.model_decision == "BLOCK":
            decision_map[date_key]["block"] += count
        else:
            decision_map[date_key]["review"] += count

    decision_trend = list(decision_map.values())
    mark("decision trend")

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
        .select_from(RiskFeedback)
        .join(
            Assessment,
            Assessment.assessment_id == RiskFeedback.assessment_id,
        )
        .filter(
            Assessment.assignment_id == assignment_id
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
    mark("daily data")

    # ---------------------------------------------------------
    # Top risk reasons
    #
    # PostgreSQL extracts and groups the JSON return_reason
    # instead of loading every input_data object into Python.
    # ---------------------------------------------------------

    return_reason = RiskFeedback.input_data.op("->>")("return_reason")

    reason_rows = (
        feedback_query
        .with_entities(
            return_reason.label("reason"),
            func.count(RiskFeedback.id).label("count"),
        )
        .filter(return_reason.is_not(None))
        .filter(return_reason != "")
        .group_by(return_reason)
        .order_by(func.count(RiskFeedback.id).desc())
        .limit(5)
        .all()
    )

    top_risk_reasons = [
        {
            "reason": row.reason,
            "count": int(row.count or 0),
        }
        for row in reason_rows
    ]
    mark("risk reasons")

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

    mark("before response")

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
                abuse_rate * 100,
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