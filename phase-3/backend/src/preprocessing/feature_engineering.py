"""Borrower-level feature engineering utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Compute a ratio while guarding against divide-by-zero cases."""
    return numerator.astype(float) / denominator.replace({0: np.nan}).astype(float)


def engineer_main_features(app_df: pd.DataFrame) -> pd.DataFrame:
    """Create application-level derived features used by the training pipeline."""
    engineered_df = app_df.copy()
    engineered_df["DAYS_EMPLOYED"] = engineered_df["DAYS_EMPLOYED"].replace(365243, np.nan)
    engineered_df["DAYS_EMPLOYED_PERC"] = _safe_ratio(
        engineered_df["DAYS_EMPLOYED"], engineered_df["DAYS_BIRTH"]
    )
    engineered_df["INCOME_PER_PERSON"] = _safe_ratio(
        engineered_df["AMT_INCOME_TOTAL"], engineered_df["CNT_FAM_MEMBERS"]
    )
    engineered_df["ANNUITY_INCOME_RATIO"] = _safe_ratio(
        engineered_df["AMT_ANNUITY"], engineered_df["AMT_INCOME_TOTAL"]
    )
    engineered_df["CREDIT_INCOME_RATIO"] = _safe_ratio(
        engineered_df["AMT_CREDIT"], engineered_df["AMT_INCOME_TOTAL"]
    )
    return engineered_df
