"""Pydantic models for the Credit Risk AI API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

REQUIRED_FEATURES = [
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


class FeatureImpact(BaseModel):
    """Model explanation entry for one influential feature."""

    model_config = ConfigDict(protected_namespaces=())

    feature: str
    shap_value: float
    direction: str


class PredictionRequest(BaseModel):
    """Borrower payload used for both pure prediction and report generation."""

    model_config = ConfigDict(protected_namespaces=())

    applicant_id: str = Field(..., min_length=1)
    features: dict[str, Any]

    @model_validator(mode="after")
    def validate_features(self) -> "PredictionRequest":
        missing = [feature for feature in REQUIRED_FEATURES if feature not in self.features]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        if float(self.features["AMT_INCOME_TOTAL"]) <= 0:
            raise ValueError("AMT_INCOME_TOTAL must be > 0")
        if float(self.features["AMT_CREDIT"]) <= 0:
            raise ValueError("AMT_CREDIT must be > 0")
        if float(self.features["DAYS_BIRTH"]) >= 0:
            raise ValueError("DAYS_BIRTH must be negative")
        return self


class PredictionResponse(BaseModel):
    """Response returned by the ML-only scoring endpoint."""

    model_config = ConfigDict(protected_namespaces=())

    risk_score: float
    risk_class: str
    confidence: float
    top_features: list[FeatureImpact]
    model_version: str


class HealthResponse(BaseModel):
    """Response returned by the API health endpoint."""

    model_config = ConfigDict(protected_namespaces=())

    status: str
    model_version: str
    uptime_seconds: float


class ModelInfoResponse(BaseModel):
    """Serialized evaluation metrics consumed by the UI."""

    model_config = ConfigDict(protected_namespaces=())

    model_version: str
    rf_recall: float
    rf_precision: float
    rf_f1: float
    rf_roc_auc: float
    rf_threshold: float
    rf_confusion_matrix: list[list[int]]
    rf_roc_curve: dict[str, list[float]]
    lr_recall: float
    lr_precision: float
    lr_f1: float
    lr_roc_auc: float
    lr_threshold: float
    lr_confusion_matrix: list[list[int]]
    lr_roc_curve: dict[str, list[float]]
    train_shape: list[int]
    test_shape: list[int]


class PreprocessResponse(BaseModel):
    """Debug response for a preprocessing-only run."""

    model_config = ConfigDict(protected_namespaces=())

    output_path: str
    rows: int
    columns: int


class ReportResponse(BaseModel):
    """Full agentic lending response."""

    model_config = ConfigDict(protected_namespaces=())

    applicant_id: str
    prediction: PredictionResponse
    report: dict[str, Any]
    processing_steps: list[str]
    error_flags: list[str]
