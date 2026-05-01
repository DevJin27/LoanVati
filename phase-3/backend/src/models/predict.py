"""Inference wrapper for the trained Credit Risk AI model."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


class CreditRiskPredictor:
    """Load the trained CatBoost pipeline once and expose a single predict interface.

    The artifact filename (rf_pipeline.joblib) is intentionally unchanged —
    renaming it would break the Render deployment. The underlying model is
    now CatBoost (catboost_v2.0), targeting ~0.80 ROC-AUC on Home Credit.
    """

    def __init__(self, models_path: str | Path = "models") -> None:
        self.models_path = Path(models_path)
        self.preprocessor_bundle = joblib.load(self.models_path / "preprocessor.joblib")
        self.lr_pipeline = joblib.load(self.models_path / "lr_pipeline.joblib")

        # Prefer CatBoost + SHAP when available; fall back to LR-only inference
        # so deployment does not require catboost/shap runtime wheels.
        self.rf_pipeline = None
        self.shap_bundle = None
        self.shap_explainer = None
        self.uses_shap = False
        try:
            self.rf_pipeline = joblib.load(self.models_path / "rf_pipeline.joblib")
            self.shap_bundle = joblib.load(self.models_path / "shap_explainer.joblib")
            self.shap_explainer = self.shap_bundle["explainer"]
            self.transformed_feature_names = self.shap_bundle["transformed_feature_names"]
            self.uses_shap = True
        except Exception:
            self.transformed_feature_names = self.preprocessor_bundle.get(
                "transformed_feature_names", []
            )

        with (self.models_path / "threshold.json").open("r", encoding="utf-8") as handle:
            threshold_payload = json.load(handle)
        self.threshold = float(threshold_payload["threshold"])
        base_version = threshold_payload.get("model_version", "catboost_v2.0")
        self.model_version = base_version if self.uses_shap else f"{base_version}_lr_fallback"

        self.feature_names = list(
            self.preprocessor_bundle["feature_names"]
        )

    def _align_features(self, feature_dict: dict) -> pd.DataFrame:
        """Align partial borrower input to the exact schema seen during training."""
        aligned = pd.DataFrame([feature_dict])
        for feature_name in self.feature_names:
            if feature_name not in aligned.columns:
                aligned[feature_name] = np.nan
        aligned = aligned.reindex(columns=self.feature_names)
        return aligned

    def _extract_shap_values(self, transformed_row: object) -> np.ndarray:
        """Normalize SHAP output formats across sklearn/shap versions."""
        if self.shap_explainer is None:
            raise ValueError("SHAP explainer unavailable in fallback mode")
        shap_values = self.shap_explainer.shap_values(transformed_row)
        if isinstance(shap_values, list):
            return np.asarray(shap_values[1])[0]

        array = np.asarray(shap_values)
        if array.ndim == 3:
            if array.shape[-1] > 1:
                return array[0, :, 1]
            return array[0, :, 0]
        if array.ndim == 2:
            return array[0]
        raise ValueError("Unexpected SHAP output shape")

    @staticmethod
    def _clean_feature_name(raw_name: str) -> str:
        """Convert sklearn pipeline feature names to human-readable labels.

        Examples:
            categorical_low__NAME_EDUCATION_TYPE_Higher education
                -> Education Type: Higher Education
            numeric__DAYS_BIRTH  -> Age (Days)
            numeric__EXT_SOURCE_2 -> External Score 2
            numeric__AMT_CREDIT   -> Credit Amount
        """
        # Strip transformer prefix (numeric__, categorical_low__, categorical_high__)
        name = raw_name
        for prefix in ("numeric__", "categorical_low__", "categorical_high__"):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # Known field renames for clarity
        RENAMES = {
            "DAYS_BIRTH": "Applicant Age",
            "DAYS_EMPLOYED": "Employment Duration",
            "AMT_CREDIT": "Credit Amount",
            "AMT_INCOME_TOTAL": "Annual Income",
            "AMT_ANNUITY": "Annual Annuity",
            "EXT_SOURCE_1": "External Credit Score 1",
            "EXT_SOURCE_2": "External Credit Score 2",
            "EXT_SOURCE_3": "External Credit Score 3",
            "CNT_FAM_MEMBERS": "Family Members",
        }

        # Check if the base column (before any OHE suffix) is in RENAMES
        for key, label in RENAMES.items():
            if name == key or name.startswith(key + "_"):
                suffix = name[len(key):].replace("_", " ").strip()
                return f"{label}: {suffix}" if suffix else label

        # Generic: replace underscores, title-case
        return name.replace("_", " ").title()

    def _top_features(self, transformed_row: object) -> list[dict[str, object]]:
        """Return the five most influential transformed features for the current row."""
        if self.uses_shap:
            values = self._extract_shap_values(transformed_row)
            value_label = "shap_value"
        else:
            classifier = self.lr_pipeline.named_steps["classifier"]
            coefficients = np.asarray(classifier.coef_)[0]
            dense_row = transformed_row.toarray()[0] if hasattr(transformed_row, "toarray") else np.asarray(transformed_row)[0]
            values = dense_row * coefficients
            value_label = "impact"

        ranked_indexes = np.argsort(np.abs(values))[-5:][::-1]

        top_features: list[dict[str, object]] = []
        for index in ranked_indexes:
            impact_value = float(values[index])
            raw_name = self.transformed_feature_names[index]
            payload = {
                "feature": self._clean_feature_name(raw_name),
                "direction": "increases risk" if impact_value >= 0 else "decreases risk",
            }
            payload[value_label] = round(impact_value, 4)
            if value_label == "impact":
                payload["shap_value"] = round(impact_value, 4)
            top_features.append(payload)
        return top_features

    def predict(self, feature_dict: dict) -> dict[str, object]:
        """Score a borrower and explain the decision with SHAP feature impacts."""
        aligned_features = self._align_features(feature_dict)
        model_pipeline = self.rf_pipeline if self.rf_pipeline is not None else self.lr_pipeline
        probability = float(model_pipeline.predict_proba(aligned_features)[:, 1][0])

        if abs(probability - self.threshold) < 0.10:
            risk_class = "Uncertain — Manual Review Required"
        elif probability < 0.30:
            risk_class = "Low"
        elif probability < 0.60:
            risk_class = "Medium"
        else:
            risk_class = "High"

        transformed_row = model_pipeline.named_steps["preprocessor"].transform(
            aligned_features
        )
        top_features = self._top_features(transformed_row)

        return {
            "risk_score": round(probability, 4),
            "risk_class": risk_class,
            "confidence": round(float(max(probability, 1 - probability)), 4),
            "top_features": top_features,
            "model_version": self.model_version,
        }
