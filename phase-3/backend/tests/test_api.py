"""API tests for prediction, validation, and health endpoints."""

from __future__ import annotations

from unittest.mock import patch


def test_health_endpoint_no_auth(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_requires_valid_api_key(client, sample_request: dict) -> None:
    response = client.post("/api/v1/predict", json=sample_request)
    assert response.status_code == 401


def test_predict_returns_valid_schema(client, sample_request: dict, test_api_key: str) -> None:
    with patch("src.api.routes.get_predictor") as mock_predictor:
        mock_predictor.return_value.predict.return_value = {
            "risk_score": 0.42,
            "risk_class": "Medium",
            "confidence": 0.58,
            "top_features": [
                {
                    "feature": "AMT_CREDIT",
                    "shap_value": 0.18,
                    "direction": "increases risk",
                }
            ]
            * 5,
            "model_version": "rf_v2.0",
        }
        response = client.post(
            "/api/v1/predict",
            json=sample_request,
            headers={"X-API-Key": test_api_key},
        )
    assert response.status_code == 200
    payload = response.json()
    assert "risk_score" in payload
    assert "risk_class" in payload
    assert "top_features" in payload


def test_invalid_input_returns_422(client, test_api_key: str) -> None:
    bad_request = {
        "applicant_id": "TEST",
        "features": {
            "AMT_INCOME_TOTAL": -1,
            "AMT_CREDIT": 100000,
            "AMT_ANNUITY": 10000,
            "CNT_FAM_MEMBERS": 2,
            "DAYS_BIRTH": -12000,
            "DAYS_EMPLOYED": -2000,
            "NAME_INCOME_TYPE": "Working",
            "NAME_EDUCATION_TYPE": "Higher education",
            "NAME_FAMILY_STATUS": "Married",
            "NAME_HOUSING_TYPE": "House / apartment",
        },
    }
    response = client.post(
        "/api/v1/predict",
        json=bad_request,
        headers={"X-API-Key": test_api_key},
    )
    assert response.status_code == 422
