"""Pydantic schemas for the Phase 3 product API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RiskClass = Literal["Low", "Uncertain", "High"]
Decision = Literal["submitted", "skipped", "submitted_override"]
LenderOutcome = Literal["approved", "rejected_credit", "rejected_other"]


class ScreeningRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    income: float = Field(..., gt=0)
    credit_amount: float = Field(..., gt=0)
    annuity: float = Field(..., gt=0)
    employment_years: float = Field(..., ge=0)
    age_years: float = Field(..., ge=18, le=100)
    family_size: int = Field(..., ge=1, le=10)
    education: str
    income_type: str
    housing_type: str
    occupation: str | None = None
    family_status: str = "Married"


class DecisionRequest(BaseModel):
    decision: Decision


class OutcomeRequest(BaseModel):
    lender_outcome: LenderOutcome
    lender_name: str | None = Field(default=None, max_length=255)


class FeatureImpactResponse(BaseModel):
    feature: str
    shap_value: float
    direction: str


class ReportQuotaResponse(BaseModel):
    plan: str
    reports_used_this_month: int
    reports_limit: int | None
    reports_remaining: int | None
    period_reset_at: datetime


class ApplicantSummaryResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    full_name: str | None
    income: float
    credit_amount: float
    risk_score: float
    risk_class: str
    dsa_decision: str | None
    lender_outcome: str | None
    status: str


class ApplicantDetailResponse(ApplicantSummaryResponse):
    model_config = ConfigDict(protected_namespaces=())

    annuity: float
    employment_years: float
    age_years: float
    family_size: int
    education: str
    income_type: str
    housing_type: str
    occupation: str | None
    family_status: str
    confidence: float
    model_version: str
    shap_top_features: list[FeatureImpactResponse]
    feature_payload: dict[str, Any]
    final_report: dict[str, Any] | None
    processing_steps: list[str]
    error_flags: list[str]
    lender_name: str | None
    outcome_logged_at: datetime | None
    include_in_training: bool


class ApplicantListResponse(BaseModel):
    items: list[ApplicantSummaryResponse]
    page: int
    limit: int
    total: int


class CoachingRequest(BaseModel):
    applicant_id: uuid.UUID


class CoachingTipResponse(BaseModel):
    feature: str
    current_value: float
    suggested_value: float
    score_improvement: float
    human_tip: str


class CoachingResponse(BaseModel):
    tips: list[CoachingTipResponse]
    current_score: float
    best_achievable_score: float
