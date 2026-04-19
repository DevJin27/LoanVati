"""Full preprocessing pipeline for borrower feature construction."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder, StandardScaler

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.preprocessing.aggregations import (
    aggregate_bureau,
    aggregate_bureau_balance,
    aggregate_credit_card,
    aggregate_installments,
    aggregate_pos_cash,
    aggregate_previous_applications,
)
from src.preprocessing.dataset import (
    DEFAULT_PROCESSED_DIR,
    resolve_processed_dir,
    resolve_raw_file,
)
from src.preprocessing.feature_engineering import engineer_main_features
from src.preprocessing.validate_data import validate_raw_data

NUMERIC_CORRELATION_THRESHOLD = 0.95
NULL_DROP_THRESHOLD = 0.50
LOW_CARDINALITY_THRESHOLD = 10
NEAR_ZERO_VARIANCE_THRESHOLD = 0.01


def _load_csv(role: str, raw_path: str | Path | None = None, usecols: list[str] | None = None) -> pd.DataFrame:
    """Load a mapped raw CSV from the preserved Home Credit directory."""
    file_path = resolve_raw_file(role, raw_path)
    return pd.read_csv(file_path, usecols=usecols, low_memory=False)


def _drop_high_null_columns(features: pd.DataFrame) -> pd.DataFrame:
    null_rates = features.isnull().mean()
    keep_columns = null_rates[null_rates <= NULL_DROP_THRESHOLD].index.tolist()
    return features.loc[:, keep_columns]


def _drop_near_zero_variance_columns(features: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = features.select_dtypes(include=["number", "bool"]).columns
    if not len(numeric_columns):
        return features

    filled_numeric = features.loc[:, numeric_columns].copy()
    filled_numeric = filled_numeric.fillna(filled_numeric.median(numeric_only=True))
    variances = filled_numeric.var(numeric_only=True)
    keep_numeric = variances[variances >= NEAR_ZERO_VARIANCE_THRESHOLD].index.tolist()

    keep_columns = keep_numeric + [
        column for column in features.columns if column not in numeric_columns
    ]
    return features.loc[:, keep_columns]


def _drop_highly_correlated_columns(features: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = features.select_dtypes(include=["number", "bool"]).columns
    if len(numeric_columns) < 2:
        return features

    filled_numeric = features.loc[:, numeric_columns].copy()
    filled_numeric = filled_numeric.fillna(filled_numeric.median(numeric_only=True))
    correlation_matrix = filled_numeric.corr().abs()
    upper_triangle = correlation_matrix.where(
        np.triu(np.ones(correlation_matrix.shape), k=1).astype(bool)
    )
    drop_columns = [
        column
        for column in upper_triangle.columns
        if upper_triangle[column].gt(NUMERIC_CORRELATION_THRESHOLD).any()
    ]
    return features.drop(columns=drop_columns)


def build_full_feature_matrix(
    raw_path: str | Path | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Build the training feature matrix from the mapped raw Home Credit tables."""
    assert validate_raw_data(raw_path, check_row_counts=False), "Raw data mapping is invalid"

    application_df = _load_csv("application_train", raw_path)
    engineered_df = engineer_main_features(application_df).set_index("SK_ID_CURR")
    target = engineered_df.pop("TARGET")

    bureau_df = _load_csv(
        "bureau",
        raw_path,
        usecols=[
            "SK_ID_CURR",
            "SK_ID_BUREAU",
            "AMT_CREDIT_SUM",
            "CREDIT_DAY_OVERDUE",
            "AMT_CREDIT_SUM_DEBT",
            "AMT_CREDIT_SUM_OVERDUE",
        ],
    )
    bureau_balance_df = _load_csv(
        "bureau_balance", raw_path, usecols=["SK_ID_BUREAU", "STATUS"]
    )
    previous_application_df = _load_csv(
        "previous_application",
        raw_path,
        usecols=["SK_ID_CURR", "NAME_CONTRACT_STATUS", "AMT_CREDIT"],
    )
    installments_df = _load_csv(
        "installments",
        raw_path,
        usecols=[
            "SK_ID_CURR",
            "DAYS_INSTALMENT",
            "DAYS_ENTRY_PAYMENT",
            "AMT_INSTALMENT",
            "AMT_PAYMENT",
        ],
    )
    credit_card_df = _load_csv(
        "credit_card_balance",
        raw_path,
        usecols=[
            "SK_ID_CURR",
            "AMT_BALANCE",
            "AMT_CREDIT_LIMIT_ACTUAL",
            "AMT_PAYMENT_TOTAL_CURRENT",
            "AMT_INST_MIN_REGULARITY",
        ],
    )
    pos_cash_df = _load_csv(
        "pos_cash_balance",
        raw_path,
        usecols=["SK_ID_CURR", "NAME_CONTRACT_STATUS", "MONTHS_BALANCE", "SK_DPD"],
    )

    aggregated_frames = [
        aggregate_bureau(bureau_df),
        aggregate_bureau_balance(bureau_balance_df, bureau_df),
        aggregate_previous_applications(previous_application_df),
        aggregate_installments(installments_df),
        aggregate_credit_card(credit_card_df),
        aggregate_pos_cash(pos_cash_df),
    ]

    feature_frame = engineered_df
    for aggregated_df in aggregated_frames:
        feature_frame = feature_frame.join(aggregated_df, how="left")

    assert feature_frame.index.is_unique, "Duplicate SK_ID_CURR rows found after merge"

    feature_frame = _drop_high_null_columns(feature_frame)
    feature_frame = _drop_near_zero_variance_columns(feature_frame)
    feature_frame = _drop_highly_correlated_columns(feature_frame)

    null_rate = feature_frame.isnull().mean().mean()
    assert null_rate < 0.10, f"Too many nulls after preprocessing: {null_rate:.2%}"
    print(f"Feature matrix ready: {feature_frame.shape}, null rate={null_rate:.2%}")
    return feature_frame, target


def build_sklearn_pipeline(
    feature_frame: pd.DataFrame | None = None, model_type: str = "rf"
) -> Pipeline:
    """Build a preprocessing pipeline tuned for the requested estimator family."""
    if feature_frame is None:
        raise ValueError("feature_frame is required to build the sklearn pipeline")

    categorical_columns = feature_frame.select_dtypes(include=["object", "category"]).columns
    numeric_columns = [
        column for column in feature_frame.columns if column not in categorical_columns
    ]

    low_cardinality_columns = [
        column
        for column in categorical_columns
        if feature_frame[column].nunique(dropna=True) <= LOW_CARDINALITY_THRESHOLD
    ]
    high_cardinality_columns = [
        column for column in categorical_columns if column not in low_cardinality_columns
    ]

    numeric_steps: list[tuple[str, object]] = [
        ("imputer", SimpleImputer(strategy="median")),
    ]
    if model_type == "lr":
        numeric_steps.append(("scaler", StandardScaler()))

    transformers: list[tuple[str, object, list[str]]] = []
    if numeric_columns:
        transformers.append(("numeric", Pipeline(numeric_steps), numeric_columns))
    if low_cardinality_columns:
        transformers.append(
            (
                "categorical_low",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OneHotEncoder(
                                handle_unknown="ignore",
                                sparse_output=False,
                            ),
                        ),
                    ]
                ),
                low_cardinality_columns,
            )
        )
    if high_cardinality_columns:
        transformers.append(
            (
                "categorical_high",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OrdinalEncoder(
                                handle_unknown="use_encoded_value",
                                unknown_value=-1,
                            ),
                        ),
                    ]
                ),
                high_cardinality_columns,
            )
        )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                ColumnTransformer(transformers=transformers, remainder="drop"),
            )
        ]
    )


if __name__ == "__main__":
    features, target = build_full_feature_matrix()
    assert features.shape[0] == 307_511, f"Row count mismatch: {features.shape[0]}"
    processed_dir = resolve_processed_dir(DEFAULT_PROCESSED_DIR)
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_path = processed_dir / "train_processed.parquet"
    features.assign(TARGET=target).to_parquet(output_path)
    null_rate = features.isnull().mean().mean()
    print(f"Saved processed matrix to {output_path}")
    print(f"Feature matrix: {features.shape}, null rate: {null_rate:.2%}")
    print(f"Class balance: {target.value_counts(normalize=True).round(4).to_dict()}")
