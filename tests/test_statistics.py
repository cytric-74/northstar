import numpy as np
import pandas as pd

from app.statistics import (
    profile_dataframe,
    numeric_summary,
    categorical_summary,
    correlation_matrix,
    top_correlations,
    missing_by_column,
    value_counts_frame,
    distribution_reference,
)


def _frame():
    return pd.DataFrame({
        "value": [1.0, 2.0, 3.0, 4.0, 100.0, np.nan],
        "paired": [2.0, 4.0, 6.0, 8.0, 200.0, 12.0],
        "label": ["a", "a", "b", "b", "c", None],
        "constant": [5, 5, 5, 5, 5, 5],
    })


def test_profile_counts_types_and_missing():
    profile = profile_dataframe(_frame())
    assert profile["rows"] == 6
    assert profile["cols"] == 4
    assert profile["numeric"] == 3
    assert profile["categorical"] == 1
    assert profile["missing"] == 2
    assert profile["missing_pct"] > 0


def test_numeric_summary_flags_outlier():
    summary = numeric_summary(_frame())
    value_row = summary[summary["Column"] == "value"].iloc[0]
    assert value_row["Count"] == 5
    assert value_row["Outliers"] >= 1
    assert value_row["Missing %"] > 0


def test_categorical_summary_top_value():
    summary = categorical_summary(_frame())
    label_row = summary[summary["Column"] == "label"].iloc[0]
    assert label_row["Unique"] == 3
    assert label_row["Top value"] == "a"
    assert label_row["Frequency"] == 2


def test_correlation_drops_constant_columns():
    corr = correlation_matrix(_frame())
    assert "constant" not in corr.columns
    assert corr.loc["value", "paired"] > 0.9


def test_top_correlations_sorted_by_strength():
    tops = top_correlations(_frame(), limit=5)
    assert not tops.empty
    assert abs(tops.iloc[0]["Correlation"]) >= abs(tops.iloc[-1]["Correlation"])


def test_missing_and_value_counts_and_reference():
    missing = missing_by_column(_frame())
    assert "value" in set(missing["Column"])
    counts = value_counts_frame(_frame(), "label", top_n=2)
    assert list(counts.columns) == ["label", "Count"]
    assert counts["Count"].iloc[0] == 2
    ref = distribution_reference(_frame()["value"])
    assert ref["median"] == 3.0


def test_correlation_matrix_empty_when_insufficient():
    single = pd.DataFrame({"only": [1, 2, 3], "text": ["a", "b", "c"]})
    assert correlation_matrix(single).empty
