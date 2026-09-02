from __future__ import annotations

from typing import Any

from backend.app.schemas.risk import (
    UnifiedRiskEvidence,
    UnifiedRiskResult,
    VisionAssessmentResult,
)


def build_unified_risk_result(
    prediction: dict[str, Any],
    vision: dict[str, Any] | None = None,
) -> UnifiedRiskResult:
    """
    Build the unified RiskGuard result.

    The XGBoost model remains the authoritative source for:
        - risk_score
        - risk_level
        - prediction
        - decision threshold
        - business decision

    SHAP and Vision are supporting evidence only.

    Vision is optional and must never independently change
    the model's risk decision.
    """

    required_fields = {
        "risk_score",
        "risk_level",
        "prediction",
        "decision_threshold",
        "decision",
        "action",
        "reason",
        "top_risk_signals",
    }

    missing = sorted(
        field
        for field in required_fields
        if field not in prediction
    )

    if missing:
        raise ValueError(
            "Prediction is missing required unified-risk fields: "
            f"{missing}"
        )

    vision_result: VisionAssessmentResult | None = None

    if vision is not None:
        vision_result = VisionAssessmentResult(**vision)

    evidence = UnifiedRiskEvidence(
        model_risk_score=float(prediction["risk_score"]),
        decision_threshold=float(
            prediction["decision_threshold"]
        ),
        model_prediction=str(prediction["prediction"]),
        top_risk_signals=prediction["top_risk_signals"],
        vision=vision_result,
    )

    return UnifiedRiskResult(
        risk_score=float(prediction["risk_score"]),
        risk_level=str(prediction["risk_level"]),
        decision=str(prediction["decision"]),
        action=str(prediction["action"]),
        reason=str(prediction["reason"]),
        evidence=evidence,
    )