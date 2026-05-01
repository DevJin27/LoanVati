"""SQLAlchemy models for LoanVati Phase 3."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def next_month() -> datetime:
    return utcnow() + timedelta(days=30)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default="dsa", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    quota: Mapped["ReportQuota"] = relationship(back_populates="user", cascade="all, delete-orphan")
    applicants: Mapped[list["Applicant"]] = relationship(back_populates="dsa_user")


class ReportQuota(Base):
    __tablename__ = "report_quota"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    plan: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    reports_used_this_month: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reports_limit: Mapped[int | None] = mapped_column(Integer, default=10)
    period_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=next_month, nullable=False)

    user: Mapped[User] = relationship(back_populates="quota")


class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dsa_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    full_name: Mapped[str | None] = mapped_column(String(255))
    income: Mapped[float] = mapped_column(Float, nullable=False)
    credit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    annuity: Mapped[float] = mapped_column(Float, nullable=False)
    employment_years: Mapped[float] = mapped_column(Float, nullable=False)
    age_years: Mapped[float] = mapped_column(Float, nullable=False)
    family_size: Mapped[int] = mapped_column(Integer, nullable=False)
    education: Mapped[str] = mapped_column(String(128), nullable=False)
    income_type: Mapped[str] = mapped_column(String(128), nullable=False)
    housing_type: Mapped[str] = mapped_column(String(128), nullable=False)
    occupation: Mapped[str | None] = mapped_column(String(128))
    family_status: Mapped[str] = mapped_column(String(128), default="Married", nullable=False)

    feature_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_class: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    shap_top_features: Mapped[list] = mapped_column(JSONB, nullable=False)
    final_report: Mapped[dict | None] = mapped_column(JSONB)
    processing_steps: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    error_flags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    dsa_decision: Mapped[str | None] = mapped_column(String(32))
    lender_outcome: Mapped[str | None] = mapped_column(String(32))
    lender_name: Mapped[str | None] = mapped_column(String(255))
    outcome_logged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    include_in_training: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    dsa_user: Mapped[User] = relationship(back_populates="applicants")


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("version", name="uq_model_versions_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    training_sample_count: Mapped[int | None] = mapped_column(Integer)
    roc_auc: Mapped[float | None] = mapped_column(Float)
    recall: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    artifact_path: Mapped[str | None] = mapped_column(Text)


class TrainingRun(Base):
    __tablename__ = "training_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(32), nullable=False)
    new_labels_used: Mapped[int | None] = mapped_column(Integer)
    base_model_version: Mapped[str | None] = mapped_column(String(64))
    output_model_version: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
