"""Focused Phase 3 product tests that do not require a live PostgreSQL server."""

from __future__ import annotations

import json
import os

os.environ.setdefault("DATABASE_URL", "postgresql://loanvati:loanvati@localhost:5432/loanvati_test")
os.environ.setdefault("JWT_SECRET", "test-secret")

from src.agent.nodes import _clean_json_text, call_json_with_retry
from src.api.auth import hash_password, verify_password
from src.api.product_routes import _normalize_risk_class, _screening_to_features, training_flag
from src.api.product_schemas import ScreeningRequest
from src.models.coaching import generate_coaching_tips


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("correct-password")
    assert verify_password("correct-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_screening_payload_maps_to_model_features() -> None:
    payload = ScreeningRequest(
        full_name="Ravi Sharma",
        income=180000,
        credit_amount=500000,
        annuity=42000,
        employment_years=5,
        age_years=33,
        family_size=2,
        education="Higher education",
        income_type="Working",
        housing_type="House / apartment",
        family_status="Married",
    )
    features = _screening_to_features(payload)
    assert features["AMT_INCOME_TOTAL"] == 180000
    assert features["AMT_CREDIT"] == 500000
    assert features["DAYS_BIRTH"] < 0
    assert features["NAME_EDUCATION_TYPE"] == "Higher education"


def test_training_flag_logic() -> None:
    assert training_flag("submitted", "approved")
    assert training_flag("submitted_override", "rejected_credit")
    assert not training_flag("submitted", "rejected_other")
    assert not training_flag("skipped", "approved")


def test_risk_class_normalization() -> None:
    assert _normalize_risk_class("Uncertain - Manual Review Required") == "Uncertain"
    assert _normalize_risk_class("Medium") == "Uncertain"
    assert _normalize_risk_class("High") == "High"
    assert _normalize_risk_class("Low") == "Low"


def test_json_retry_recovers_from_markdown(monkeypatch) -> None:
    monkeypatch.setattr(
        "src.agent.nodes._invoke_prompt",
        lambda *_args: "```json\n" + json.dumps({"risk_analysis": "ok", "retrieval_query": "rbi credit review"}) + "\n```",
    )
    parsed = call_json_with_retry("system", "user", ["risk_analysis", "retrieval_query"])
    assert parsed["risk_analysis"] == "ok"
    assert _clean_json_text("```json\n{\"a\": 1}\n```") == '{"a": 1}'


def test_coaching_returns_actionable_tip() -> None:
    class Predictor:
        def predict(self, features: dict) -> dict:
            return {"risk_score": 0.50 if features["AMT_CREDIT"] < 500000 else 0.72}

    tips = generate_coaching_tips(
        {"feature_payload": {"AMT_CREDIT": 500000, "AMT_ANNUITY": 42000}, "risk_score": 0.72},
        Predictor(),  # type: ignore[arg-type]
    )
    assert tips
    assert tips[0]["feature"] in {"credit_amount", "annuity"}
    assert tips[0]["score_improvement"] > 0.05
