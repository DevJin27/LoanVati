"""Inference wrapper for the trained Credit Risk AI model."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


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

    def _validate_features(self, feature_dict: dict) -> None:
        """Warn on unexpected features; error on none of the expected features present.

        Extra keys are safe — _align_features drops them via reindex.
        Missing keys become NaN and are imputed — warn so the caller knows.
        A hard raise only fires if the input shares zero columns with training,
        which almost certainly means the wrong schema was passed.
        """
        known = set(self.feature_names)
        provided = set(feature_dict.keys())
        extra = provided - known
        missing = known - provided
        if extra:
            logger.debug("Extra features ignored by model: %s", extra)
        if missing:
            logger.warning(
                "%d features missing from input (will be median-imputed): %s",
                len(missing),
                missing,
            )
        if not provided.intersection(known):
            raise ValueError(
                f"Input shares no columns with the trained schema. "
                f"Expected subset of: {known}"
            )

    def _guardrails(self, feature_dict: dict) -> str | None:
        """Hard business-rule checks applied before the model runs.

        Returns a flag string when a rule fires, or None when the input
        should proceed to the model unchanged.

        Flags:
            APPROVE_SAFE   — ratios are so low the model will agree
            REJECT_RISK    — ratios are so extreme the model is unreliable
            MANUAL_REVIEW  — implausible input magnitude, needs human check
        """
        income = float(feature_dict.get("AMT_INCOME_TOTAL") or 0)
        credit = float(feature_dict.get("AMT_CREDIT") or 0)
        annuity = float(feature_dict.get("AMT_ANNUITY") or 0)

        if income <= 0:
            return "REJECT_RISK"  # cannot score without income

        dti = credit / income   # debt-to-income
        pti = annuity / income  # payment-to-income

        # Safe zone: low debt burden — approve without model to avoid false positives
        # threshold widened from dti<0.05 to dti<=0.08 to catch high-income / small-loan cases
        # (e.g. ₹1.8Cr income, ₹9L credit → dti=0.05 was previously excluded by strict <)
        if dti <= 0.08 and pti <= 0.15:
            return "APPROVE_SAFE"

        # Structurally unviable — model extrapolation unreliable beyond these levels
        if dti > 20.0 or pti > 0.80:
            return "REJECT_RISK"

        # Income above 10 Cr (₹100M) — outside training distribution, flag for human
        if income > 1e8:
            return "MANUAL_REVIEW"

        return None

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
        self._validate_features(feature_dict)

        # Hard business-rule guardrails — checked before the model runs.
        guardrail_flag = self._guardrails(feature_dict)
        if guardrail_flag == "APPROVE_SAFE":
            return {
                "risk_score": 0.05,
                "risk_class": "Low",
                "confidence": 1.0,
                "top_features": [],
                "model_version": f"{self.model_version}_guardrail",
            }
        if guardrail_flag == "REJECT_RISK":
            return {
                "risk_score": 0.95,
                "risk_class": "High",
                "confidence": 1.0,
                "top_features": [],
                "model_version": f"{self.model_version}_guardrail",
            }
        if guardrail_flag == "MANUAL_REVIEW":
            return {
                "risk_score": 0.50,
                "risk_class": "Uncertain — Manual Review Required",
                "confidence": 0.0,
                "top_features": [],
                "model_version": f"{self.model_version}_guardrail",
            }

        aligned_features = self._align_features(feature_dict)
        model_pipeline = self.rf_pipeline if self.rf_pipeline is not None else self.lr_pipeline
        probability = float(model_pipeline.predict_proba(aligned_features)[:, 1][0])

        # Post-model safety override.
        # If the model fires High but the financial ratios are clearly safe,
        # the model is extrapolating badly (likely due to INCOME_PER_PERSON or raw income magnitude).
        # Hard-cap at Low when both ratios are unambiguously safe.
        income = float(feature_dict.get("AMT_INCOME_TOTAL") or 0)
        credit = float(feature_dict.get("AMT_CREDIT") or 0)
        annuity = float(feature_dict.get("AMT_ANNUITY") or 0)
        if income > 0:
            dti_post = credit / income
            pti_post = annuity / income
            if dti_post <= 0.05 and pti_post <= 0.05 and probability > self.threshold:
                logger.warning(
                    "Post-model override fired: model=%.3f but dti=%.3f pti=%.3f — forcing Low",
                    probability, dti_post, pti_post,
                )
                return {
                    "risk_score": round(min(probability, 0.20), 4),
                    "risk_class": "Low",
                    "confidence": round(abs(0.10 - 0.5) * 2, 4),
                    "top_features": [],
                    "model_version": f"{self.model_version}_override",
                }

        # Threshold-relative bucketing.
        # self.threshold is the FPR-constrained optimal from training (currently 0.43).
        # Uncertain band = 70% of threshold so the boundary adapts if threshold changes.
        uncertain_low = self.threshold * 0.70
        if probability >= self.threshold:
            risk_class = "High"
        elif probability >= uncertain_low:
            risk_class = "Uncertain — Manual Review Required"
        else:
            risk_class = "Low"

        # True confidence = how far from the decision boundary (0.5).
        # max(p, 1-p) was wrong: it gave 0.55 a "confidence" of 0.55.
        # abs(p - 0.5) * 2 gives 0.0 at boundary, 1.0 at either extreme.
        confidence = round(abs(probability - 0.5) * 2, 4)

        transformed_row = model_pipeline.named_steps["preprocessor"].transform(
            aligned_features
        )
        top_features = self._top_features(transformed_row)

        return {
            "risk_score": round(probability, 4),
            "risk_class": risk_class,
            "confidence": confidence,
            "top_features": top_features,
            "model_version": self.model_version,
        }
