import pandas as pd
import pytest

from app.data_quality import clean_sales_data, dataframe_to_csv_bytes


def test_clean_sales_data_handles_common_quality_problems():
    source = pd.DataFrame(
        {
            " date ": ["2026-01-01", "bad-date", "2026-01-03", "2026-01-03"],
            "order id": ["O-1", "O-2", "O-3", "O-3"],
            "Product": ["Laptop", "Phone", None, None],
            "Revenue": ["$1,000", "500", None, None],
            "Cost": ["700", "300", "100", "100"],
            "Profit": [None, "200", None, None],
        }
    )

    cleaned, summary, column_report, actions = clean_sales_data(source)

    assert len(cleaned) == 2
    assert list(cleaned["Order_ID"]) == ["O-1", "O-3"]
    assert cleaned["Product"].tolist() == ["Laptop", "Unknown"]
    assert cleaned["Revenue"].notna().all()
    assert cleaned["Profit"].tolist() == [300.0, 900.0]
    assert summary["duplicate_rows_removed"] == 1
    assert summary["invalid_dates_found"] == 1
    assert summary["missing_values_after"] == 0
    assert "Column" in column_report.columns
    assert actions


def test_dataframe_to_csv_bytes_formats_dates():
    source = pd.DataFrame({"Date": pd.to_datetime(["2026-01-01"]), "Revenue": [100]})

    result = dataframe_to_csv_bytes(source).decode("utf-8")

    assert "2026-01-01" in result


def test_clean_sales_data_supports_mixed_dates_and_rejects_ambiguous_columns():
    source = pd.DataFrame(
        {"Date": ["2026-01-01", "02/03/2026"], "Revenue": [100, 200]}
    )
    cleaned, _, _, _ = clean_sales_data(source)
    assert len(cleaned) == 2
    assert cleaned["Date"].notna().all()

    with pytest.raises(ValueError, match="Ambiguous input"):
        clean_sales_data(pd.DataFrame({"Date": ["2026-01-01"], " date ": ["2026-01-01"]}))

    with pytest.raises(ValueError, match="No usable sales rows"):
        clean_sales_data(pd.DataFrame({"Date": ["not-a-date"], "Revenue": [100]}))

    with pytest.raises(ValueError, match="usable data rows and columns"):
        clean_sales_data(pd.DataFrame(index=[0]))


def test_dataframe_to_csv_bytes_handles_string_dates():
    result = dataframe_to_csv_bytes(pd.DataFrame({"Date": ["2026-01-01"], "Revenue": [100]})).decode("utf-8")
    assert "2026-01-01" in result
