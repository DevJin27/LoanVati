"""Aggregation utilities for Home Credit supporting tables."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _flatten_columns(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Normalize aggregated column names and add the requested prefix."""
    flattened: list[str] = []
    for column in frame.columns:
        if isinstance(column, tuple):
            parts = [str(part) for part in column if part]
            flattened.append(f"{prefix}{'_'.join(parts).lower()}")
        else:
            flattened.append(f"{prefix}{str(column).lower()}")
    frame.columns = flattened
    frame.index.name = "SK_ID_CURR"
    return frame.sort_index()


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Compute a division that preserves missing values for zero denominators."""
    return numerator.astype(float) / denominator.replace({0: np.nan}).astype(float)


def aggregate_bureau(bureau_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate bureau history to a borrower-level feature set."""
    grouped = bureau_df.groupby("SK_ID_CURR").agg(
        {
            "SK_ID_BUREAU": ["count"],
            "AMT_CREDIT_SUM": ["mean", "max", "sum"],
            "CREDIT_DAY_OVERDUE": ["mean", "max", "sum"],
            "AMT_CREDIT_SUM_DEBT": ["mean", "max", "sum"],
            "AMT_CREDIT_SUM_OVERDUE": ["mean", "max", "sum"],
        }
    )
    return _flatten_columns(grouped, "bureau_")


def aggregate_bureau_balance(
    bureau_balance_df: pd.DataFrame, bureau_df: pd.DataFrame
) -> pd.DataFrame:
    """Aggregate monthly bureau status history after joining to current borrowers."""
    bureau_keys = bureau_df.loc[:, ["SK_ID_BUREAU", "SK_ID_CURR"]].drop_duplicates()
    merged = bureau_balance_df.merge(bureau_keys, on="SK_ID_BUREAU", how="inner")

    status_map = {str(value): value for value in range(6)}
    status_map.update({"X": 0, "C": -1})
    merged["status_numeric"] = merged["STATUS"].map(status_map).fillna(0).astype(float)
    merged["status_overdue"] = merged["status_numeric"].gt(0).astype(int)

    grouped = merged.groupby("SK_ID_CURR").agg(
        {
            "status_numeric": ["mean", "max"],
            "status_overdue": ["sum"],
        }
    )
    return _flatten_columns(grouped, "bbal_")


def aggregate_previous_applications(prev_app_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate prior application outcomes and requested credit amounts."""
    work_df = prev_app_df.copy()
    work_df["is_approved"] = work_df["NAME_CONTRACT_STATUS"].eq("Approved").astype(int)
    work_df["is_rejected"] = work_df["NAME_CONTRACT_STATUS"].eq("Refused").astype(int)

    grouped = work_df.groupby("SK_ID_CURR").agg(
        {
            "is_approved": ["mean"],
            "AMT_CREDIT": ["mean", "max"],
            "is_rejected": ["sum"],
        }
    )
    return _flatten_columns(grouped, "prev_")


def aggregate_installments(installments_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate repayment performance from installment payments."""
    work_df = installments_df.copy()
    work_df["payment_ratio"] = _safe_ratio(
        work_df["AMT_PAYMENT"], work_df["AMT_INSTALMENT"]
    ).clip(lower=0, upper=2)
    work_df["days_diff"] = (
        work_df["DAYS_INSTALMENT"] - work_df["DAYS_ENTRY_PAYMENT"]
    ).astype(float)

    grouped = work_df.groupby("SK_ID_CURR").agg(
        {
            "payment_ratio": ["mean", "max", "std"],
            "days_diff": ["mean", "max", "std"],
        }
    )
    return _flatten_columns(grouped, "inst_")


def aggregate_credit_card(cc_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate credit card utilization and repayment coverage."""
    work_df = cc_df.copy()
    work_df["utilization_rate"] = _safe_ratio(
        work_df["AMT_BALANCE"], work_df["AMT_CREDIT_LIMIT_ACTUAL"]
    )
    work_df["payment_coverage"] = _safe_ratio(
        work_df["AMT_PAYMENT_TOTAL_CURRENT"], work_df["AMT_INST_MIN_REGULARITY"]
    )

    grouped = work_df.groupby("SK_ID_CURR").agg(
        {
            "utilization_rate": ["mean", "max"],
            "payment_coverage": ["mean", "max"],
        }
    )
    return _flatten_columns(grouped, "cc_")


def aggregate_pos_cash(pos_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate POS cash contract activity and delinquency features."""
    work_df = pos_df.copy()
    work_df["active_contract"] = work_df["NAME_CONTRACT_STATUS"].eq("Active").astype(int)

    grouped = work_df.groupby("SK_ID_CURR").agg(
        {
            "active_contract": ["sum"],
            "MONTHS_BALANCE": ["mean"],
            "SK_DPD": ["mean", "max"],
        }
    )
    return _flatten_columns(grouped, "pos_")
