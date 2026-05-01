"""Phase 3 product routes for applicants, coaching, and billing status."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from src.agent.graph import run_agent
from src.api.auth import get_current_user
from src.api.product_schemas import (
    ApplicantDetailResponse,
    ApplicantListResponse,
    ApplicantSummaryResponse,
    CoachingRequest,
    CoachingResponse,
    DecisionRequest,
    OutcomeRequest,
    ReportQuotaResponse,
    ScreeningRequest,
)
from src.api.routes import get_predictor
from src.db.models import Applicant, ReportQuota, User
from src.db.session import get_db
from src.models.coaching import generate_coaching_tips

router = APIRouter(prefix="/api/v1", tags=["product"])


def _normalize_risk_class(raw: str) -> str:
    lowered = raw.lower()
    if "uncertain" in lowered or "manual" in lowered or "medium" in lowered:
        return "Uncertain"
    if "high" in lowered:
        return "High"
    return "Low"


def _screening_to_features(payload: ScreeningRequest) -> dict:
    return {
        "AMT_INCOME_TOTAL": float(payload.income),
        "AMT_CREDIT": float(payload.credit_amount),
        "AMT_ANNUITY": float(payload.annuity),
        "CNT_FAM_MEMBERS": float(payload.family_size),
        "DAYS_BIRTH": -round(float(payload.age_years) * 365.25, 2),
        "DAYS_EMPLOYED": -round(float(payload.employment_years) * 365.25, 2),
        "NAME_INCOME_TYPE": payload.income_type,
        "NAME_EDUCATION_TYPE": payload.education,
        "NAME_FAMILY_STATUS": payload.family_status,
        "NAME_HOUSING_TYPE": payload.housing_type,
    }


def _get_or_create_quota(db: Session, user: User) -> ReportQuota:
    quota = db.get(ReportQuota, user.id)
    if quota is None:
        quota = ReportQuota(user_id=user.id)
        db.add(quota)
        db.flush()
    now = datetime.now(timezone.utc)
    if quota.period_reset_at <= now:
        quota.reports_used_this_month = 0
        quota.period_reset_at = now + timedelta(days=30)
    return quota


def _assert_quota_available(quota: ReportQuota) -> None:
    if quota.reports_limit is not None and quota.reports_used_this_month >= quota.reports_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Monthly report quota exhausted",
        )


def _status_for(applicant: Applicant) -> str:
    if applicant.lender_outcome == "approved":
        return "Approved"
    if applicant.lender_outcome in {"rejected_credit", "rejected_other"}:
        return "Rejected"
    if applicant.dsa_decision in {"submitted", "submitted_override"}:
        return "Submitted - pending"
    return "Not submitted"


def training_flag(decision: str | None, outcome: str | None) -> bool:
    """Return whether an applicant outcome is safe to include in retraining."""
    return decision in {"submitted", "submitted_override"} and outcome in {"approved", "rejected_credit"}


def _summary_response(applicant: Applicant) -> ApplicantSummaryResponse:
    return ApplicantSummaryResponse(
        id=applicant.id,
        created_at=applicant.created_at,
        full_name=applicant.full_name,
        income=applicant.income,
        credit_amount=applicant.credit_amount,
        risk_score=applicant.risk_score,
        risk_class=applicant.risk_class,
        dsa_decision=applicant.dsa_decision,
        lender_outcome=applicant.lender_outcome,
        status=_status_for(applicant),
    )


def _detail_response(applicant: Applicant) -> ApplicantDetailResponse:
    return ApplicantDetailResponse(
        **_summary_response(applicant).model_dump(),
        annuity=applicant.annuity,
        employment_years=applicant.employment_years,
        age_years=applicant.age_years,
        family_size=applicant.family_size,
        education=applicant.education,
        income_type=applicant.income_type,
        housing_type=applicant.housing_type,
        occupation=applicant.occupation,
        family_status=applicant.family_status,
        confidence=applicant.confidence,
        model_version=applicant.model_version,
        shap_top_features=applicant.shap_top_features,
        feature_payload=applicant.feature_payload,
        final_report=applicant.final_report,
        processing_steps=applicant.processing_steps,
        error_flags=applicant.error_flags,
        lender_name=applicant.lender_name,
        outcome_logged_at=applicant.outcome_logged_at,
        include_in_training=applicant.include_in_training,
    )


@router.post("/applicants/screen", response_model=ApplicantDetailResponse, status_code=status.HTTP_201_CREATED)
def screen_applicant(
    payload: ScreeningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicantDetailResponse:
    quota = _get_or_create_quota(db, current_user)
    _assert_quota_available(quota)

    features = _screening_to_features(payload)
    predictor = get_predictor()
    prediction = predictor.predict(features)
    normalized_risk_class = _normalize_risk_class(str(prediction["risk_class"]))
    agent_state = run_agent(features, {**prediction, "risk_class": normalized_risk_class})

    applicant = Applicant(
        dsa_user_id=current_user.id,
        full_name=payload.full_name.strip() if payload.full_name else None,
        income=payload.income,
        credit_amount=payload.credit_amount,
        annuity=payload.annuity,
        employment_years=payload.employment_years,
        age_years=payload.age_years,
        family_size=payload.family_size,
        education=payload.education,
        income_type=payload.income_type,
        housing_type=payload.housing_type,
        occupation=payload.occupation,
        family_status=payload.family_status,
        feature_payload=features,
        risk_score=float(prediction["risk_score"]),
        risk_class=normalized_risk_class,
        confidence=float(prediction["confidence"]),
        model_version=str(prediction["model_version"]),
        shap_top_features=prediction["top_features"],
        final_report=agent_state.get("final_report") or {},
        processing_steps=agent_state.get("processing_steps", []),
        error_flags=agent_state.get("error_flags", []),
    )
    quota.reports_used_this_month += 1
    db.add(applicant)
    db.commit()
    db.refresh(applicant)
    return _detail_response(applicant)


@router.get("/applicants", response_model=ApplicantListResponse)
def list_applicants(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    risk_class: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicantListResponse:
    query = select(Applicant).where(Applicant.dsa_user_id == current_user.id)
    count_query = select(func.count()).select_from(Applicant).where(Applicant.dsa_user_id == current_user.id)

    filters = []
    if risk_class:
        filters.append(Applicant.risk_class == risk_class)
    if status_filter == "submitted":
        filters.append(Applicant.dsa_decision.in_(["submitted", "submitted_override"]))
    elif status_filter == "skipped":
        filters.append(Applicant.dsa_decision == "skipped")
    elif status_filter == "pending":
        filters.append(
            Applicant.dsa_decision.in_(["submitted", "submitted_override"]),
        )
        filters.append(Applicant.lender_outcome.is_(None))
    if search:
        search_term = f"%{search.strip()}%"
        filters.append(or_(Applicant.full_name.ilike(search_term), cast(Applicant.id, String).ilike(search_term)))

    for item in filters:
        query = query.where(item)
        count_query = count_query.where(item)

    total = int(db.scalar(count_query) or 0)
    applicants = db.scalars(
        query.order_by(Applicant.created_at.desc()).offset((page - 1) * limit).limit(limit)
    ).all()
    return ApplicantListResponse(
        items=[_summary_response(applicant) for applicant in applicants],
        page=page,
        limit=limit,
        total=total,
    )


@router.get("/applicants/{applicant_id}", response_model=ApplicantDetailResponse)
def get_applicant(
    applicant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicantDetailResponse:
    applicant = db.get(Applicant, applicant_id)
    if applicant is None or applicant.dsa_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Applicant not found")
    return _detail_response(applicant)


@router.patch("/applicants/{applicant_id}/decision", response_model=ApplicantDetailResponse)
def update_decision(
    applicant_id: uuid.UUID,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicantDetailResponse:
    applicant = db.get(Applicant, applicant_id)
    if applicant is None or applicant.dsa_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Applicant not found")
    if payload.decision == "submitted" and applicant.risk_class == "High":
        applicant.dsa_decision = "submitted_override"
    else:
        applicant.dsa_decision = payload.decision
    applicant.include_in_training = training_flag(applicant.dsa_decision, applicant.lender_outcome)
    db.commit()
    db.refresh(applicant)
    return _detail_response(applicant)


@router.patch("/applicants/{applicant_id}/outcome", response_model=ApplicantDetailResponse)
def update_outcome(
    applicant_id: uuid.UUID,
    payload: OutcomeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApplicantDetailResponse:
    applicant = db.get(Applicant, applicant_id)
    if applicant is None or applicant.dsa_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Applicant not found")
    if applicant.dsa_decision not in {"submitted", "submitted_override"}:
        raise HTTPException(status_code=409, detail="Log a submitted decision before lender outcome")

    applicant.lender_outcome = payload.lender_outcome
    applicant.lender_name = payload.lender_name
    applicant.outcome_logged_at = datetime.now(timezone.utc)
    applicant.include_in_training = training_flag(applicant.dsa_decision, payload.lender_outcome)
    db.commit()
    db.refresh(applicant)
    return _detail_response(applicant)


@router.post("/coaching", response_model=CoachingResponse)
def coaching(
    payload: CoachingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CoachingResponse:
    applicant = db.get(Applicant, payload.applicant_id)
    if applicant is None or applicant.dsa_user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Applicant not found")
    if applicant.risk_class == "Low":
        return CoachingResponse(tips=[], current_score=applicant.risk_score, best_achievable_score=applicant.risk_score)

    tips = generate_coaching_tips(
        {"feature_payload": applicant.feature_payload, "risk_score": applicant.risk_score},
        get_predictor(),
    )
    best_score = round(applicant.risk_score - max([tip["score_improvement"] for tip in tips], default=0), 4)
    return CoachingResponse(tips=tips, current_score=applicant.risk_score, best_achievable_score=best_score)


@router.get("/billing/status", response_model=ReportQuotaResponse)
def billing_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportQuotaResponse:
    quota = _get_or_create_quota(db, current_user)
    db.commit()
    remaining = None if quota.reports_limit is None else max(quota.reports_limit - quota.reports_used_this_month, 0)
    return ReportQuotaResponse(
        plan=quota.plan,
        reports_used_this_month=quota.reports_used_this_month,
        reports_limit=quota.reports_limit,
        reports_remaining=remaining,
        period_reset_at=quota.period_reset_at,
    )
