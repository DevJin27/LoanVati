"""Tests for model training artifacts and inference behavior."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.predict import CreditRiskPredictor


class DummyPreprocessor:
    def transform(self, dataframe: pd.DataFrame) -> np.ndarray:
        return np.array([[0.2, -0.1, 0.05, 0.11, -0.03]], dtype=float)


class DummyPipeline:
    feature_names_in_ = np.array(
        [
            "AMT_INCOME_TOTAL",
            "AMT_CREDIT",
            "AMT_ANNUITY",
            "CNT_FAM_MEMBERS",
            "DAYS_BIRTH",
            "DAYS_EMPLOYED",
            "NAME_INCOME_TYPE",
            "NAME_EDUCATION_TYPE",
            "NAME_FAMILY_STATUS",
            "NAME_HOUSING_TYPE",
        ]
    )

    def __init__(self, probability: float = 0.62) -> None:
        self.probability = probability
        self.named_steps = {"preprocessor": DummyPreprocessor()}

    def predict_proba(self, _dataframe: pd.DataFrame) -> np.ndarray:
        return np.array([[1 - self.probability, self.probability]], dtype=float)


class DummyExplainer:
    def shap_values(self, _transformed_row: np.ndarray) -> np.ndarray:
        return np.array(
            [
                [
                    [0.0, 0.12],
                    [0.0, -0.08],
                    [0.0, 0.04],
                    [0.0, 0.02],
                    [0.0, -0.01],
                ]
            ]
        )


def build_predictor(probability: float = 0.62) -> CreditRiskPredictor:
    predictor = object.__new__(CreditRiskPredictor)
    predictor.rf_pipeline = DummyPipeline(probability=probability)
    predictor.preprocessor_bundle = {
        "feature_names": list(DummyPipeline.feature_names_in_),
        "transformed_feature_names": [
            "numeric__AMT_INCOME_TOTAL",
            "numeric__AMT_CREDIT",
            "numeric__AMT_ANNUITY",
            "numeric__CNT_FAM_MEMBERS",
            "numeric__DAYS_BIRTH",
        ],
    }
    predictor.shap_bundle = {
        "explainer": DummyExplainer(),
        "transformed_feature_names": predictor.preprocessor_bundle["transformed_feature_names"],
    }
    predictor.shap_explainer = predictor.shap_bundle["explainer"]
    predictor.transformed_feature_names = predictor.shap_bundle["transformed_feature_names"]
    predictor.threshold = 0.5
    predictor.model_version = "rf_v2.0"
    predictor.feature_names = list(DummyPipeline.feature_names_in_)
    predictor.models_path = None
    return predictor


def test_predict_output_schema(sample_feature_dict: dict) -> None:
    predictor = build_predictor()
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


def test_uncertain_flag_near_threshold(sample_feature_dict: dict) -> None:
    predictor = build_predictor(probability=0.51)
    result = predictor.predict(sample_feature_dict)
    assert result["risk_class"] == "Uncertain — Manual Review Required"
