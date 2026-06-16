"""SQLite database interface for storing cleaned sales data and KPIs."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import pandas as pd

from app.kpi_engine import kpis_to_dataframe

DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[1] / "database" / "kpi_platform.db"

def initialize_database(database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Initialize SQLite tables for storing data runs and results."""
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS kpi_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    row_count INTEGER NOT NULL,
                    growth_current_period TEXT,
                    growth_previous_period TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS kpi_results (
                    run_id TEXT NOT NULL,
                    kpi_name TEXT NOT NULL,
                    kpi_value REAL,
                    unit TEXT NOT NULL,
                    PRIMARY KEY (run_id, kpi_name),
                    FOREIGN KEY (run_id) REFERENCES kpi_runs(run_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cleaned_sales (
                    run_id TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    sales_record TEXT NOT NULL,
                    PRIMARY KEY (run_id, row_number),
                    FOREIGN KEY (run_id) REFERENCES kpi_runs(run_id)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sales_data (
                    run_id TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    Date TEXT,
                    Order_ID TEXT,
                    Customer_ID TEXT,
                    Product TEXT,
                    Category TEXT,
                    Revenue REAL,
                    Cost REAL,
                    Profit REAL,
                    Quantity INTEGER,
                    PRIMARY KEY (run_id, row_number),
                    FOREIGN KEY (run_id) REFERENCES kpi_runs(run_id)
                )
                """
            )

def _record_to_json(record: dict[str, Any]) -> str:
    """Format row dictionary to serializable JSON string."""
    serializable = {}
    for key, value in record.items():
        if pd.isna(value):
            serializable[key] = None
        elif isinstance(value, pd.Timestamp):
            serializable[key] = value.strftime("%Y-%m-%d")
        elif hasattr(value, "item"):
            serializable[key] = value.item()
        else:
            serializable[key] = value
    return json.dumps(serializable)

def save_analysis_run(
    cleaned_data: pd.DataFrame,
    kpis: dict[str, Any],
    source_name: str,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> str:
    """Persist the run summary, core KPIs, and relational sales rows to SQLite."""
    initialize_database(database_path)
    run_id = str(uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    kpi_table = kpis_to_dataframe(kpis)

    with closing(sqlite3.connect(database_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.execute(
                """
                INSERT INTO kpi_runs (
                    run_id, created_at, source_name, row_count,
                    growth_current_period, growth_previous_period
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    created_at,
                    source_name,
                    int(len(cleaned_data)),
                    kpis["growth_current_period"],
                    kpis["growth_previous_period"],
                ),
            )

            connection.executemany(
                """
                INSERT INTO kpi_results (run_id, kpi_name, kpi_value, unit)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (
                        run_id,
                        row["KPI"],
                        None if pd.isna(row["Value"]) else float(row["Value"]),
                        row["Unit"],
                    )
                    for row in kpi_table.to_dict("records")
                ],
            )

            connection.executemany(
                """
                INSERT INTO cleaned_sales (run_id, row_number, sales_record)
                VALUES (?, ?, ?)
                """,
                [
                    (run_id, row_number, _record_to_json(record))
                    for row_number, record in enumerate(
                        cleaned_data.to_dict("records"), start=1
                    )
                ],
            )

            sales_rows = []
            for row_number, row in enumerate(cleaned_data.to_dict("records"), start=1):
                date_val = None
                if "Date" in row and pd.notna(row["Date"]):
                    if isinstance(row["Date"], pd.Timestamp):
                        date_val = row["Date"].strftime("%Y-%m-%d")
                    elif isinstance(row["Date"], str):
                        date_val = row["Date"]
                    else:
                        date_val = str(row["Date"])
                
                sales_rows.append((
                    run_id,
                    row_number,
                    date_val,
                    row.get("Order_ID"),
                    row.get("Customer_ID"),
                    row.get("Product"),
                    row.get("Category"),
                    None if pd.isna(row.get("Revenue")) else float(row.get("Revenue")),
                    None if pd.isna(row.get("Cost")) else float(row.get("Cost")),
                    None if pd.isna(row.get("Profit")) else float(row.get("Profit")),
                    None if pd.isna(row.get("Quantity")) else int(row.get("Quantity")),
                ))

            connection.executemany(
                """
                INSERT INTO sales_data (
                    run_id, row_number, Date, Order_ID, Customer_ID, Product, Category, Revenue, Cost, Profit, Quantity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                sales_rows,
            )

    return run_id

def load_kpi_history(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> pd.DataFrame:
    """Query historic analysis runs from the database."""
    initialize_database(database_path)
    query = """
        SELECT
            r.created_at,
            r.source_name,
            r.row_count,
            r.growth_current_period,
            r.growth_previous_period,
            k.kpi_name,
            k.kpi_value,
            k.unit,
            r.run_id
        FROM kpi_runs AS r
        JOIN kpi_results AS k ON r.run_id = k.run_id
        ORDER BY r.created_at DESC, k.kpi_name
    """
    with closing(sqlite3.connect(database_path)) as connection:
        return pd.read_sql_query(query, connection)
