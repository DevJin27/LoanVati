"""Tests for model training artifacts and inference behavior."""

from __future__ import annotations

import numpy as np

from src.models.predict import CreditRiskPredictor


def test_predict_output_schema(models_dir, sample_feature_dict: dict) -> None:
    predictor = CreditRiskPredictor(models_path=models_dir)
    result = predictor.predict(sample_feature_dict)

    assert 0 <= result["risk_score"] <= 1
    assert result["risk_class"] in [
        "Low",
        "Medium",
        "High",
        "Uncertain — Manual Review Required",
    ]
    assert len(result["top_features"]) == 5
    assert all("shap_value" in feature for feature in result["top_features"])


def test_uncertain_flag_near_threshold(models_dir, sample_feature_dict: dict) -> None:
    predictor = CreditRiskPredictor(models_path=models_dir)
    predictor.threshold = 0.5
    predictor.rf_pipeline.predict_proba = lambda _: np.array([[0.49, 0.51]])

    result = predictor.predict(sample_feature_dict)
    assert result["risk_class"] == "Uncertain — Manual Review Required"
