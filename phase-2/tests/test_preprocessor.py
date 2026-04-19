"""Preprocessor tests for the Phase 2 data pipeline."""

from __future__ import annotations

import pandas as pd

from src.preprocessing.aggregations import (
    aggregate_bureau,
    aggregate_bureau_balance,
    aggregate_credit_card,
    aggregate_installments,
    aggregate_pos_cash,
    aggregate_previous_applications,
)
from src.preprocessing.dataset import resolve_raw_file
from src.preprocessing.feature_engineering import engineer_main_features
from src.preprocessing.validate_data import validate_raw_data


def _assert_grouped_output(frame: pd.DataFrame) -> None:
    assert isinstance(frame, pd.DataFrame)
    assert not frame.empty
    assert frame.index.name == "SK_ID_CURR"


def test_validate_raw_data_accepts_phase2_mapping() -> None:
    if not resolve_raw_file("application_train").exists():
        import pytest

        pytest.skip("Phase 2 raw dataset is not available in this environment.")
    assert validate_raw_data(check_row_counts=False)


def test_engineer_main_features_handles_employment_sentinel(
    raw_application_sample: pd.DataFrame,
) -> None:
    sample = raw_application_sample.copy()
    sample.loc[sample.index[0], "DAYS_EMPLOYED"] = 365243
    engineered = engineer_main_features(sample)
    assert pd.isna(engineered.loc[sample.index[0], "DAYS_EMPLOYED"])
    assert "CREDIT_INCOME_RATIO" in engineered.columns


def test_all_aggregations_return_sk_id_curr_index(bureau_sample: pd.DataFrame) -> None:
    if not resolve_raw_file("application_train").exists():
        import pytest

        pytest.skip("Phase 2 raw dataset is not available in this environment.")
    bureau_balance_sample = pd.read_csv(
        resolve_raw_file("bureau_balance"),
        usecols=["SK_ID_BUREAU", "STATUS"],
    )
    bureau_balance_sample = bureau_balance_sample[
        bureau_balance_sample["SK_ID_BUREAU"].isin(bureau_sample["SK_ID_BUREAU"])
    ].head(5_000)

    previous_sample = pd.read_csv(
        resolve_raw_file("previous_application"),
        nrows=5_000,
        usecols=["SK_ID_CURR", "NAME_CONTRACT_STATUS", "AMT_CREDIT"],
    )
    installments_sample = pd.read_csv(
        resolve_raw_file("installments"),
        nrows=10_000,
        usecols=[
            "SK_ID_CURR",
            "DAYS_INSTALMENT",
            "DAYS_ENTRY_PAYMENT",
            "AMT_INSTALMENT",
            "AMT_PAYMENT",
        ],
    )
    credit_card_sample = pd.read_csv(
        resolve_raw_file("credit_card_balance"),
        nrows=10_000,
        usecols=[
            "SK_ID_CURR",
            "AMT_BALANCE",
            "AMT_CREDIT_LIMIT_ACTUAL",
            "AMT_PAYMENT_TOTAL_CURRENT",
            "AMT_INST_MIN_REGULARITY",
        ],
    )
    pos_sample = pd.read_csv(
        resolve_raw_file("pos_cash_balance"),
        nrows=10_000,
        usecols=["SK_ID_CURR", "NAME_CONTRACT_STATUS", "MONTHS_BALANCE", "SK_DPD"],
    )

    outputs = [
        aggregate_bureau(bureau_sample),
        aggregate_bureau_balance(bureau_balance_sample, bureau_sample),
        aggregate_previous_applications(previous_sample),
        aggregate_installments(installments_sample),
        aggregate_credit_card(credit_card_sample),
        aggregate_pos_cash(pos_sample),
    ]

    for output in outputs:
        _assert_grouped_output(output)
