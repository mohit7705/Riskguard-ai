from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RiskPredictionRequest(BaseModel):
    data: dict[str, Any] = Field(
        ...,
        min_length=1,
        description="Return and user feature data to evaluate.",
    )


class BatchRiskPredictionRequest(BaseModel):
    data: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        description="Multiple return and user feature records to evaluate.",
    )


class RiskSignal(BaseModel):
    feature: str
    value: float | int | str | bool | None
    importance: float
    description: str


class RiskPredictionResult(BaseModel):
    predicted_label: int
    prediction: str
    abuse_probability: float
    legitimate_probability: float
    risk_score: float
    risk_level: str
    decision: str
    action: str
    reason: str
    top_risk_signals: list[RiskSignal]
    model_type: str
    review_case_id: str | None = None


class RiskPredictionResponse(BaseModel):
    status: str
    result: RiskPredictionResult


class BatchRiskPredictionResponse(BaseModel):
    status: str
    results: list[RiskPredictionResult]


class ReviewCaseResponse(BaseModel):
    case_id: str
    status: str
    created_at: str
    prediction: RiskPredictionResult
    data: dict[str, Any]
    analyst_decision: str | None = None
    analyst_reason: str | None = None
    resolved_at: str | None = None


class ReviewCaseListResponse(BaseModel):
    status: str
    cases: list[ReviewCaseResponse]


class ReviewDecisionRequest(BaseModel):
    decision: str
    reason: str | None = None
class FeedbackResponse(BaseModel):
    id: int
    case_id: str | None = None
    prediction: str
    predicted_label: int
    abuse_probability: float
    risk_score: float
    risk_level: str
    model_decision: str
    analyst_decision: str | None = None
    actual_outcome: str | None = None
    analyst_reason: str | None = None
    input_data: dict[str, Any]
    created_at: str
    outcome_recorded_at: str | None = None


class FeedbackListResponse(BaseModel):
    status: str
    records: list[FeedbackResponse]


class ActualOutcomeRequest(BaseModel):
    actual_outcome: str


class MonitoringResponse(BaseModel):
    status: str
    total_records: int
    labeled_records: int
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    false_positive_count: int
    false_negative_count: int
    true_positive_count: int
    true_negative_count: int