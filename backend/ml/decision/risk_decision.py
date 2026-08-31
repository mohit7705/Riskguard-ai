from __future__ import annotations

from typing import Any


DECISION_RULES = {
    "MINIMAL": {
        "decision": "ALLOW",
        "action": "ALLOW_RETURN",
        "reason": "Risk is minimal and does not require intervention.",
    },
    "LOW": {
        "decision": "ALLOW",
        "action": "ALLOW_RETURN",
        "reason": "Risk is low and does not require manual review.",
    },
    "MEDIUM": {
        "decision": "REVIEW",
        "action": "MANUAL_REVIEW",
        "reason": "Moderate risk requires manual review.",
    },
    "HIGH": {
        "decision": "REVIEW",
        "action": "MANUAL_REVIEW",
        "reason": "High abuse risk requires manual review.",
    },
    "CRITICAL": {
        "decision": "BLOCK",
        "action": "BLOCK_RETURN",
        "reason": "Critical abuse risk requires blocking the return.",
    },
}


def make_risk_decision(
    prediction: dict[str, Any],
) -> dict[str, str]:
    """
    Convert a RiskGuard model prediction into a
    business decision.
    """

    risk_level = prediction.get("risk_level")

    if not isinstance(risk_level, str):
        raise ValueError(
            "Prediction is missing a valid risk_level."
        )

    risk_level = risk_level.upper()

    if risk_level not in DECISION_RULES:
        raise ValueError(
            f"Unsupported risk level: {risk_level}"
        )

    rule = DECISION_RULES[risk_level]

    return {
        "decision": rule["decision"],
        "action": rule["action"],
        "reason": rule["reason"],
    }
