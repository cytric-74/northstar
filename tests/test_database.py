import sqlite3
from contextlib import closing

import pandas as pd

from app.database import load_kpi_history, save_analysis_run
from app.kpi_engine import calculate_kpis


def test_save_analysis_run_persists_sales_and_kpis(tmp_path):
    database_path = tmp_path / "test.db"
    cleaned_data = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-02-01"]),
            "Order_ID": ["O-1", "O-2"],
            "Customer_ID": ["C-1", "C-2"],
            "Revenue": [100, 150],
            "Profit": [20, 30],
        }
    )
    kpis = calculate_kpis(cleaned_data)

    run_id = save_analysis_run(cleaned_data, kpis, "sales.csv", database_path)
    history = load_kpi_history(database_path)

    with closing(sqlite3.connect(database_path)) as connection:
        sales_rows = connection.execute("SELECT COUNT(*) FROM cleaned_sales").fetchone()[0]
        kpi_rows = connection.execute("SELECT COUNT(*) FROM kpi_results").fetchone()[0]

    assert run_id
    assert sales_rows == 2
    assert kpi_rows == 7
    assert len(history) == 7
    assert set(history["source_name"]) == {"sales.csv"}

    database_path.unlink()
    assert not database_path.exists()
