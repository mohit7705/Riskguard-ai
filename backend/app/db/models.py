from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    assignment_number: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )

    assignment_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Assessment(Base):
    __tablename__ = "assessments"

    assessment_id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )

    assignment_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )

    assessment_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    total_records: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RiskFeedback(Base):
    __tablename__ = "risk_feedback"

    assessment_id: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    case_id: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    prediction: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    predicted_label: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    abuse_probability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    risk_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    model_decision: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    analyst_decision: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    actual_outcome: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    analyst_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    input_data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    outcome_recorded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

class ReviewCase(Base):
    __tablename__ = "review_cases"

    case_id: Mapped[str] = mapped_column(
        String(32),
        primary_key=True,
    )

    assessment_id: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="OPEN",
        index=True,
    )

    prediction: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    data: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )

    analyst_decision: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )

    analyst_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )