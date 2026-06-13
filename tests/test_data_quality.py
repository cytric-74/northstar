import pandas as pd

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
