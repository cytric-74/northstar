"""Data quality and cleaning operations for raw sales datasets."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any
import pandas as pd

EXPECTED_COLUMNS = [
    "Date",
    "Order_ID",
    "Customer_ID",
    "Product",
    "Category",
    "Revenue",
    "Cost",
    "Profit",
    "Quantity",
]
NUMERIC_COLUMNS = ["Revenue", "Cost", "Profit", "Quantity"]
TEXT_COLUMNS = ["Order_ID", "Customer_ID", "Product", "Category"]

def load_data(filepath: str | Path) -> pd.DataFrame:
    return pd.read_csv(filepath)

def check_missing_values(data: pd.DataFrame) -> pd.Series:
    return data.isna().sum()

def check_duplicates(data: pd.DataFrame) -> int:
    return int(data.duplicated().sum())

def validate_dates(data: pd.DataFrame) -> int:
    if "Date" not in data.columns:
        return 0
    return int(pd.to_datetime(data["Date"], errors="coerce").isna().sum())

def generate_quality_report(data: pd.DataFrame) -> dict[str, Any]:
    return {
        "Total Rows": int(len(data)),
        "Missing Values": check_missing_values(data).to_dict(),
        "Duplicate Rows": check_duplicates(data),
        "Invalid Dates": validate_dates(data),
    }

def standardize_column_names(data: pd.DataFrame) -> pd.DataFrame:
    cleaned = data.copy()
    expected_lookup = {
        re.sub(r"[^a-z0-9]", "", column.lower()): column
        for column in EXPECTED_COLUMNS
    }
    renamed_columns = {}
    for column in cleaned.columns:
        normalized = re.sub(r"[^a-z0-9]", "", str(column).strip().lower())
        renamed_columns[column] = expected_lookup.get(normalized, str(column).strip())
    return cleaned.rename(columns=renamed_columns)

def _clean_numeric_series(series: pd.Series) -> pd.Series:
    text_values = series.astype("string").str.strip()
    text_values = text_values.str.replace(r"[$,]", "", regex=True)
    text_values = text_values.replace({"": pd.NA, "None": pd.NA, "nan": pd.NA})
    return pd.to_numeric(text_values, errors="coerce")

def _quality_score(data: pd.DataFrame) -> float:
    if data.empty or data.shape[1] == 0:
        return 0.0
    populated_cells = int(data.notna().sum().sum())
    total_cells = int(data.shape[0] * data.shape[1])
    return round((populated_cells / total_cells) * 100, 1)

def build_column_report(before: pd.DataFrame, after: pd.DataFrame) -> pd.DataFrame:
    rows = []
    all_columns = list(dict.fromkeys([*before.columns, *after.columns]))
    for column in all_columns:
        before_series = before[column] if column in before else pd.Series(dtype="object")
        after_series = after[column] if column in after else pd.Series(dtype="object")
        rows.append(
            {
                "Column": column,
                "Data Type After Cleaning": str(after_series.dtype),
                "Missing Before": int(before_series.isna().sum()),
                "Missing After": int(after_series.isna().sum()),
                "Unique Values After": int(after_series.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)

def clean_sales_data(
    data: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, Any], pd.DataFrame, list[str]]:
    """Clean data and return standard tables plus operational logs."""
    if data.empty:
        raise ValueError("The uploaded CSV does not contain any data rows.")

    original = standardize_column_names(data)
    cleaned = original.copy()
    actions: list[str] = []

    duplicate_rows = int(cleaned.duplicated().sum())
    if duplicate_rows:
        cleaned = cleaned.drop_duplicates().copy()
        actions.append(f"Removed {duplicate_rows} duplicate rows.")

    object_columns = cleaned.select_dtypes(include=["object", "string"]).columns
    for column in object_columns:
        cleaned[column] = cleaned[column].astype("string").str.strip()
        cleaned[column] = cleaned[column].replace("", pd.NA)

    invalid_dates = 0
    if "Date" in cleaned.columns:
        original_dates = cleaned["Date"].copy()
        cleaned["Date"] = pd.to_datetime(cleaned["Date"], errors="coerce")
        invalid_dates = int(original_dates.notna().sum() - cleaned["Date"].notna().sum())
        unusable_date_rows = int(cleaned["Date"].isna().sum())
        if unusable_date_rows:
            cleaned = cleaned.dropna(subset=["Date"]).copy()
            actions.append(f"Removed {unusable_date_rows} rows with invalid dates.")
    else:
        actions.append("Date column not supplied; date validation skipped.")

    for column in NUMERIC_COLUMNS:
        if column not in cleaned.columns:
            continue
        cleaned[column] = _clean_numeric_series(cleaned[column])
        if column == "Profit" and {"Revenue", "Cost"}.issubset(cleaned.columns):
            derived_profit = cleaned["Revenue"] - cleaned["Cost"]
            missing_profit = int(cleaned[column].isna().sum())
            cleaned[column] = cleaned[column].fillna(derived_profit)
            if missing_profit:
                actions.append(f"Derived {missing_profit} missing Profit values as Revenue - Cost.")
        missing_numeric = int(cleaned[column].isna().sum())
        if missing_numeric:
            median = cleaned[column].median()
            fill_value = float(median) if pd.notna(median) else 0.0
            cleaned[column] = cleaned[column].fillna(fill_value)
            actions.append(f"Filled {missing_numeric} empty {column} rows with median ({fill_value:,.2f}).")

    for column in TEXT_COLUMNS:
        if column not in cleaned.columns:
            continue
        missing_text = int(cleaned[column].isna().sum())
        if missing_text:
            cleaned[column] = cleaned[column].fillna("Unknown")
            actions.append(f"Replaced {missing_text} empty {column} values with 'Unknown'.")

    cleaned = cleaned.sort_values("Date") if "Date" in cleaned.columns else cleaned
    cleaned = cleaned.reset_index(drop=True)
    missing_expected = [column for column in EXPECTED_COLUMNS if column not in cleaned]
    if missing_expected:
        actions.append("Optional expected columns missing: " + ", ".join(missing_expected))

    summary = {
        "rows_before": int(len(original)),
        "rows_after": int(len(cleaned)),
        "columns": int(cleaned.shape[1]),
        "duplicate_rows_removed": duplicate_rows,
        "invalid_dates_found": invalid_dates,
        "missing_values_before": int(original.isna().sum().sum()),
        "missing_values_after": int(cleaned.isna().sum().sum()),
        "quality_score_before": _quality_score(original),
        "quality_score_after": _quality_score(cleaned),
        "missing_expected_columns": missing_expected,
    }
    return cleaned, summary, build_column_report(original, cleaned), actions

def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    cleaned, _, _, _ = clean_sales_data(data)
    return cleaned

def dataframe_to_csv_bytes(data: pd.DataFrame) -> bytes:
    export = data.copy()
    if "Date" in export.columns:
        export["Date"] = export["Date"].dt.strftime("%Y-%m-%d")
    return export.to_csv(index=False).encode("utf-8")
