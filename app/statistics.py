from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


def profile_dataframe(data: pd.DataFrame) -> dict[str, Any]:
    rows, cols = data.shape
    numeric = data.select_dtypes(include="number").shape[1]
    datetime_cols = data.select_dtypes(include=["datetime", "datetimetz"]).shape[1]
    categorical = cols - numeric - datetime_cols
    total_cells = (rows * cols) or 1
    missing = int(data.isna().sum().sum())
    return {
        "rows": rows,
        "cols": cols,
        "numeric": numeric,
        "categorical": max(categorical, 0),
        "datetime": datetime_cols,
        "missing": missing,
        "missing_pct": missing / total_cells * 100,
        "duplicates": int(data.duplicated().sum()),
        "memory_kb": float(data.memory_usage(deep=True).sum()) / 1024,
    }


def numeric_summary(data: pd.DataFrame) -> pd.DataFrame:
    numeric = data.select_dtypes(include="number")
    records: list[dict[str, Any]] = []
    for column in numeric.columns:
        series = numeric[column].dropna()
        if series.empty:
            continue
        q1, q3 = float(series.quantile(0.25)), float(series.quantile(0.75))
        iqr = q3 - q1
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        outliers = int(((series < low) | (series > high)).sum())
        records.append({
            "Column": column,
            "Count": int(series.count()),
            "Mean": float(series.mean()),
            "Median": float(series.median()),
            "Std": float(series.std()) if series.count() > 1 else 0.0,
            "Min": float(series.min()),
            "Q1": q1,
            "Q3": q3,
            "Max": float(series.max()),
            "IQR": iqr,
            "Skew": float(series.skew()) if series.count() > 2 else 0.0,
            "Kurtosis": float(series.kurt()) if series.count() > 3 else 0.0,
            "Missing %": float(data[column].isna().mean() * 100),
            "Unique": int(series.nunique()),
            "Outliers": outliers,
        })
    return pd.DataFrame(records)


def categorical_summary(data: pd.DataFrame) -> pd.DataFrame:
    categorical = data.select_dtypes(exclude="number")
    records: list[dict[str, Any]] = []
    for column in categorical.columns:
        series = data[column]
        counts = series.value_counts(dropna=True)
        top_value = str(counts.index[0]) if not counts.empty else "—"
        top_freq = int(counts.iloc[0]) if not counts.empty else 0
        records.append({
            "Column": column,
            "Unique": int(series.nunique(dropna=True)),
            "Top value": top_value,
            "Frequency": top_freq,
            "Dominance %": float(top_freq / len(series) * 100) if len(series) else 0.0,
            "Missing %": float(series.isna().mean() * 100),
        })
    return pd.DataFrame(records)


def correlation_matrix(data: pd.DataFrame) -> pd.DataFrame:
    numeric = data.select_dtypes(include="number")
    numeric = numeric.loc[:, numeric.nunique() > 1]
    if numeric.shape[1] < 2:
        return pd.DataFrame()
    return numeric.corr(numeric_only=True)


def top_correlations(data: pd.DataFrame, limit: int = 8) -> pd.DataFrame:
    corr = correlation_matrix(data)
    if corr.empty:
        return pd.DataFrame(columns=["Feature A", "Feature B", "Correlation"])
    columns = corr.columns.tolist()
    pairs: list[dict[str, Any]] = []
    for i in range(len(columns)):
        for j in range(i + 1, len(columns)):
            value = corr.iloc[i, j]
            if pd.notna(value):
                pairs.append({"Feature A": columns[i], "Feature B": columns[j], "Correlation": float(value)})
    frame = pd.DataFrame(pairs)
    if frame.empty:
        return frame
    frame["strength"] = frame["Correlation"].abs()
    return frame.sort_values("strength", ascending=False).drop(columns="strength").head(limit).reset_index(drop=True)


def missing_by_column(data: pd.DataFrame) -> pd.DataFrame:
    missing = data.isna().sum()
    missing = missing[missing > 0].sort_values(ascending=False)
    if missing.empty:
        return pd.DataFrame(columns=["Column", "Missing", "Missing %"])
    return pd.DataFrame({
        "Column": missing.index.astype(str),
        "Missing": missing.values.astype(int),
        "Missing %": (missing.values / len(data) * 100),
    })


def value_counts_frame(data: pd.DataFrame, column: str, top_n: int = 10) -> pd.DataFrame:
    if column not in data.columns:
        return pd.DataFrame(columns=[column, "Count"])
    counts = data[column].value_counts(dropna=True).head(top_n)
    return pd.DataFrame({column: counts.index.astype(str), "Count": counts.values.astype(int)})


def distribution_reference(series: pd.Series) -> dict[str, float]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {"mean": float("nan"), "median": float("nan"), "std": float("nan")}
    return {
        "mean": float(clean.mean()),
        "median": float(clean.median()),
        "std": float(clean.std()) if clean.count() > 1 else 0.0,
    }
