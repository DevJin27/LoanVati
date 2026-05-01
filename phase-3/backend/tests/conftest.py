"""Shared pytest fixtures for the Phase 2 test suite."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ.setdefault("API_SECRET_KEY", "phase2-test-key")

from src.api.main import app
from src.preprocessing.dataset import PHASE_ROOT, resolve_raw_file


@pytest.fixture(scope="session")
def phase2_root() -> Path:
    """Return the Phase 2 project root."""
    return PHASE_ROOT


@pytest.fixture(scope="session")
def raw_application_sample() -> pd.DataFrame:
    """Load a small real sample from application_train for fast local tests."""
    return pd.read_csv(resolve_raw_file("application_train"), nrows=512, low_memory=False)


@pytest.fixture(scope="session")
def bureau_sample() -> pd.DataFrame:
    """Load a small bureau sample containing keys for downstream aggregation tests."""
    return pd.read_csv(
        resolve_raw_file("bureau"),
        nrows=2_000,
        usecols=[
            "SK_ID_CURR",
            "SK_ID_BUREAU",
            "AMT_CREDIT_SUM",
            "CREDIT_DAY_OVERDUE",
            "AMT_CREDIT_SUM_DEBT",
            "AMT_CREDIT_SUM_OVERDUE",
        ],
    )


@pytest.fixture(scope="session")
def models_dir(phase2_root: Path) -> Path:
    """Return the trained models directory."""
    return phase2_root / "models"


@pytest.fixture(scope="session")
def sample_feature_dict() -> dict:
    """Return a synthetic but realistic borrower payload for API/model tests."""
    return {
        "AMT_INCOME_TOTAL": 180000.0,
        "AMT_CREDIT": 500000.0,
        "AMT_ANNUITY": 42000.0,
        "CNT_FAM_MEMBERS": 2.0,
        "DAYS_BIRTH": -12000.0,
        "DAYS_EMPLOYED": -2500.0,
        "NAME_INCOME_TYPE": "Working",
        "NAME_EDUCATION_TYPE": "Higher education",
        "NAME_FAMILY_STATUS": "Married",
        "NAME_HOUSING_TYPE": "House / apartment",
    }


@pytest.fixture(scope="session")
def test_api_key() -> str:
    return "phase2-test-key"


@pytest.fixture(scope="session")
def sample_request(sample_feature_dict: dict) -> dict:
    required_keys = [
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
    return {
        "applicant_id": "TEST-001",
        "features": {key: sample_feature_dict[key] for key in required_keys},
    }


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
