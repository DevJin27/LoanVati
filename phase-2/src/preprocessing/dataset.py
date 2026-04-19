"""Dataset mapping helpers for the Phase 2 Home Credit files."""

from __future__ import annotations

from pathlib import Path

PHASE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_DIR = PHASE_ROOT / "Data "
DEFAULT_PROCESSED_DIR = PHASE_ROOT / "data" / "processed"

RAW_FILE_MAP: dict[str, str] = {
    "application_train": "HC_application_train.csv",
    "bureau": "HC_bureau.csv",
    "bureau_balance": "HC_bureau_balance.csv",
    "previous_application": "HC_previous_application.csv",
    "installments": "HC_installments_payments.csv",
    "credit_card_balance": "HC_credit_card_balance.csv",
    "pos_cash_balance": "HC_POS_CASH_balance.csv",
    "column_description": "HomeCredit_columns_description.csv",
    "sample_submission": "HC_sample_submission.csv",
}

REQUIRED_FILE_SPECS: dict[str, dict[str, object]] = {
    "application_train": {
        "file_name": RAW_FILE_MAP["application_train"],
        "min_rows": 300_000,
        "required_cols": ["SK_ID_CURR", "TARGET"],
    },
    "bureau": {
        "file_name": RAW_FILE_MAP["bureau"],
        "min_rows": 1_000_000,
        "required_cols": ["SK_ID_CURR", "SK_ID_BUREAU"],
    },
    "bureau_balance": {
        "file_name": RAW_FILE_MAP["bureau_balance"],
        "min_rows": 1_000_000,
        "required_cols": ["SK_ID_BUREAU", "STATUS"],
    },
    "previous_application": {
        "file_name": RAW_FILE_MAP["previous_application"],
        "min_rows": 100_000,
        "required_cols": ["SK_ID_CURR", "SK_ID_PREV"],
    },
    "installments": {
        "file_name": RAW_FILE_MAP["installments"],
        "min_rows": 1_000_000,
        "required_cols": ["SK_ID_PREV", "SK_ID_CURR", "AMT_PAYMENT"],
    },
    "credit_card_balance": {
        "file_name": RAW_FILE_MAP["credit_card_balance"],
        "min_rows": 100_000,
        "required_cols": ["SK_ID_PREV", "SK_ID_CURR"],
    },
    "pos_cash_balance": {
        "file_name": RAW_FILE_MAP["pos_cash_balance"],
        "min_rows": 1_000_000,
        "required_cols": ["SK_ID_PREV", "SK_ID_CURR"],
    },
    "column_description": {
        "file_name": RAW_FILE_MAP["column_description"],
        "min_rows": 100,
        "required_cols": ["Table", "Row", "Description"],
    },
    "sample_submission": {
        "file_name": RAW_FILE_MAP["sample_submission"],
        "min_rows": 10_000,
        "required_cols": ["SK_ID_CURR", "TARGET"],
    },
}


def resolve_raw_dir(raw_path: str | Path | None = None) -> Path:
    """Return the raw data directory, defaulting to the preserved `Data ` folder."""
    return Path(raw_path) if raw_path is not None else DEFAULT_RAW_DIR


def resolve_processed_dir(processed_path: str | Path | None = None) -> Path:
    """Return the processed output directory for generated artifacts."""
    return Path(processed_path) if processed_path is not None else DEFAULT_PROCESSED_DIR


def resolve_raw_file(role: str, raw_path: str | Path | None = None) -> Path:
    """Resolve a canonical dataset role to the actual Phase 2 filename."""
    if role not in RAW_FILE_MAP:
        raise KeyError(f"Unknown raw dataset role: {role}")
    return resolve_raw_dir(raw_path) / RAW_FILE_MAP[role]
