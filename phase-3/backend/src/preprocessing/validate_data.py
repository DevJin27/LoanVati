"""Validate the presence and minimal structure of the Phase 2 raw dataset."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.preprocessing.dataset import REQUIRED_FILE_SPECS, resolve_raw_dir, resolve_raw_file


def _read_header(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        return next(csv.reader(handle))


def _count_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return sum(1 for _ in handle) - 1


def validate_raw_data(
    raw_path: str | Path | None = None, check_row_counts: bool = True
) -> bool:
    """Validate required files, headers, and approximate dataset sizes."""
    raw_dir = resolve_raw_dir(raw_path)
    print(f"Checking raw data directory: {raw_dir}")

    all_passed = True
    for role, spec in REQUIRED_FILE_SPECS.items():
        file_path = resolve_raw_file(role, raw_dir)
        if not file_path.exists():
            print(f"FAIL missing file: {file_path.name}")
            all_passed = False
            continue

        header = _read_header(file_path)
        missing_columns = [column for column in spec["required_cols"] if column not in header]
        if missing_columns:
            print(f"FAIL {file_path.name} missing columns: {missing_columns}")
            all_passed = False
            continue

        if check_row_counts:
            row_count = _count_rows(file_path)
            min_rows = int(spec["min_rows"])
            if row_count < min_rows:
                print(
                    f"FAIL {file_path.name} has {row_count} rows; expected at least {min_rows}"
                )
                all_passed = False
                continue
            print(f"OK {file_path.name}: {row_count} rows, required columns present")
        else:
            print(f"OK {file_path.name}: required columns present")

    return all_passed


if __name__ == "__main__":
    validated = validate_raw_data()
    assert validated, "Data validation failed. Fix missing files before proceeding."
    print("\nAll data files validated successfully")
