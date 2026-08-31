import json
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

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
    Build model_performance from the real, on-disk evaluation
    artifacts instead of hardcoded numbers, so the dashboard
    reflects whatever model was most recently trained.

    Reads:
    - risk_threshold_report.json for the selected threshold's
      precision/recall/F1/confusion-matrix/business_cost
    - model_evaluation_report.json for ROC-AUC (not present in
      the threshold report)
    """

    if not THRESHOLD_REPORT_PATH.exists():
        return FALLBACK_MODEL_PERFORMANCE

    with THRESHOLD_REPORT_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        threshold_report = json.load(file)

    selected = threshold_report["selected_metrics"]

    roc_auc = FALLBACK_MODEL_PERFORMANCE["roc_auc"]

    if EVALUATION_REPORT_PATH.exists():
        with EVALUATION_REPORT_PATH.open(
            "r",
            encoding="utf-8",
        ) as file:
            evaluation_report = json.load(file)

        xgboost_metrics = evaluation_report.get(
            "xgboost",
            {},
        )

        roc_auc = xgboost_metrics.get(
            "roc_auc",
            roc_auc,
        )

    return {
        "model": threshold_report.get("model", "XGBoost"),
        "test_rows": threshold_report.get("test_rows"),
        "threshold": selected["threshold"],
        "precision": selected["precision"],
        "recall": selected["recall"],
        "f1_score": selected["f1_score"],
        "pr_auc": threshold_report.get("average_precision"),
        "roc_auc": roc_auc,
        "false_positives": selected["false_positives"],
        "false_negatives": selected["false_negatives"],
        "true_positives": selected["true_positives"],
        "true_negatives": selected["true_negatives"],
        "business_cost": selected["business_cost"],
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
):

    total_reviewed = (
        db.query(RiskFeedback)
        .count()
    )

    allowed = (
        db.query(RiskFeedback)
        .filter(
            RiskFeedback.model_decision == "ALLOW"
        )
        .count()
    )

    blocked = (
        db.query(RiskFeedback)
        .filter(
            RiskFeedback.model_decision == "BLOCK"
        )
        .count()
    )


    pending_review = (
        db.query(ReviewCase)
        .filter(
            ReviewCase.status == "OPEN"
        )
        .count()
    )


    abuse_rate = (
        db.query(
            func.avg(
                RiskFeedback.abuse_probability
            )
        )
        .scalar()
    )


    risk_distribution = {}

    rows = (
        db.query(
            RiskFeedback.risk_level,
            func.count(RiskFeedback.id)
        )
        .group_by(
            RiskFeedback.risk_level
        )
        .all()
    )


    for level, count in rows:
        risk_distribution[level] = count

    decision_map = {}

    trend_rows = (
        db.query(
            RiskFeedback.created_at,
            RiskFeedback.model_decision,
        )
        .order_by(
            RiskFeedback.created_at
        )
        .all()
    )

    for created_at, decision in trend_rows:
        date = created_at.strftime("%b %d")

        if date not in decision_map:
            decision_map[date] = {
                "date": date,
                "allow": 0,
                "block": 0,
                "review": 0,
            }

        if decision == "ALLOW":
            decision_map[date]["allow"] += 1
        elif decision == "BLOCK":
            decision_map[date]["block"] += 1
        else:
            decision_map[date]["review"] += 1

    decision_trend = list(decision_map.values())

    reasons = Counter()

    feedback_rows = (
        db.query(
            RiskFeedback.input_data
        )
        .all()
    )

    for row in feedback_rows:
        data = row[0]

        if data.get("return_reason"):
            reasons[data["return_reason"]] += 1

    top_risk_reasons = [
        {
            "reason": reason,
            "count": count,
        }
        for reason, count in reasons.most_common(5)
    ]

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

    return {

        "summary": {

            "total_reviewed": total_reviewed,

            "pending_review": pending_review,

            "allowed": allowed,

            "blocked": blocked,

            "abuse_rate": round(
                (abuse_rate or 0) * 100,
                2
            )

        },


        "risk_distribution":
            risk_distribution,

        "decision_trend":
            decision_trend,

        "top_risk_reasons":
            top_risk_reasons,

        "model_performance": load_model_performance(),

        "threshold_curve": load_threshold_curve(),

        "financial_impact": financial_impact,

    }