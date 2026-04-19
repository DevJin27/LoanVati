"""Shared pytest fixtures for the Phase 2 test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
def sample_feature_dict(raw_application_sample: pd.DataFrame) -> dict:
    """Build a realistic partial borrower payload from the raw application table."""
    row = raw_application_sample.drop(columns=["TARGET"]).iloc[0]
    return row.where(pd.notnull(row), None).to_dict()
