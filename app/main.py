"""Streamlit entry point for Phases 1 and 2 of the KPI Intelligence Platform."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx


if __name__ == "__main__" and get_script_run_ctx(suppress_warning=True) is None:
    project_root = Path(__file__).resolve().parents[1]
    raise SystemExit(
        subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(Path(__file__).resolve())],
            cwd=project_root,
        )
    )

from app.data_quality import clean_sales_data, dataframe_to_csv_bytes
from app.database import DEFAULT_DATABASE_PATH, load_kpi_history, save_analysis_run
from app.kpi_engine import KPI_DEFINITIONS, calculate_kpis, kpis_to_dataframe


def format_currency(value: float | None) -> str:
    """Format a KPI value as currency for Streamlit cards."""
    return "N/A" if value is None or pd.isna(value) else f"${value:,.2f}"


def format_percent(value: float | None) -> str:
    """Format a KPI value as a percentage for Streamlit cards."""
    return "N/A" if value is None or pd.isna(value) else f"{value:,.2f}%"


def format_kpi_table(kpi_table: pd.DataFrame) -> pd.DataFrame:
    """Create a reader-friendly KPI table without changing numeric results."""
    display = kpi_table.copy()
    display["Value"] = display.apply(
        lambda row: (
            format_currency(row["Value"])
            if row["Unit"] == "currency"
            else format_percent(row["Value"])
            if row["Unit"] == "percent"
            else "N/A"
            if pd.isna(row["Value"])
            else f"{int(row['Value']):,}"
        ),
        axis=1,
    )
    return display


st.set_page_config(page_title="KPI Intelligence Platform", page_icon="KPI", layout="wide")
st.title("KPI Intelligence Platform")
st.subheader("Phases 1 and 2: Data Quality and KPI Engine")
st.write(
    "Upload a CSV file to clean sales data, generate a quality report, "
    "calculate KPIs, and optionally save the analysis to SQLite."
)

with st.expander("Expected sales columns"):
    st.write(
        "`Date`, `Order_ID`, `Customer_ID`, `Product`, `Category`, `Revenue`, "
        "`Cost`, `Profit`, `Quantity`"
    )

uploaded_file = st.file_uploader("Upload sales data", type=["csv"])
if uploaded_file is None:
    st.info("Upload a CSV file to begin. You can use `data/raw/sales_data.csv`.")
    st.stop()

try:
    raw_data = pd.read_csv(uploaded_file)
except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as error:
    st.error(f"The CSV could not be read: {error}")
    st.stop()

st.success(f"Loaded {len(raw_data):,} rows and {raw_data.shape[1]:,} columns.")
with st.expander("Preview uploaded data", expanded=True):
    st.dataframe(raw_data.head(20), use_container_width=True)

try:
    cleaned_data, summary, column_report, actions = clean_sales_data(raw_data)
except ValueError as error:
    st.error(str(error))
    st.stop()

st.header("Data Quality Summary")
quality_metrics = st.columns(5)
quality_metrics[0].metric("Rows Before", f"{summary['rows_before']:,}")
quality_metrics[1].metric("Rows After", f"{summary['rows_after']:,}")
quality_metrics[2].metric("Duplicates Removed", f"{summary['duplicate_rows_removed']:,}")
quality_metrics[3].metric("Invalid Dates", f"{summary['invalid_dates_found']:,}")
quality_metrics[4].metric(
    "Quality Score",
    f"{summary['quality_score_after']:.1f}%",
    f"{summary['quality_score_after'] - summary['quality_score_before']:.1f} pts",
)

left_column, right_column = st.columns(2)
with left_column:
    st.subheader("Cleaning Actions")
    for action in actions:
        st.write(f"- {action}")
with right_column:
    st.subheader("Missing Values")
    st.write(f"Before cleaning: **{summary['missing_values_before']:,}**")
    st.write(f"After cleaning: **{summary['missing_values_after']:,}**")
    if summary["missing_expected_columns"]:
        st.warning("Optional expected columns not supplied: " + ", ".join(summary["missing_expected_columns"]))
    else:
        st.success("All expected sales columns were supplied.")

st.subheader("Column-Level Quality Report")
st.dataframe(column_report, use_container_width=True, hide_index=True)
st.subheader("Cleaned Data Preview")
st.dataframe(cleaned_data.head(50), use_container_width=True)
st.download_button(
    "Download cleaned sales data",
    dataframe_to_csv_bytes(cleaned_data),
    "cleaned_sales_data.csv",
    "text/csv",
)

st.divider()
st.header("KPI Engine")
try:
    kpis = calculate_kpis(cleaned_data)
except ValueError as error:
    st.error(str(error))
    st.stop()

first_kpi_row = st.columns(4)
first_kpi_row[0].metric("Revenue", format_currency(kpis["revenue"]))
first_kpi_row[1].metric("Profit", format_currency(kpis["profit"]))
first_kpi_row[2].metric("Profit Margin", format_percent(kpis["profit_margin"]))
first_kpi_row[3].metric("Average Order Value", format_currency(kpis["average_order_value"]))
second_kpi_row = st.columns(3)
second_kpi_row[0].metric("Orders", f"{kpis['orders']:,}")
second_kpi_row[1].metric("Customers", f"{kpis['customers']:,}")
second_kpi_row[2].metric("Monthly Growth Rate", format_percent(kpis["growth_rate"]))

if kpis["growth_rate"] is None:
    st.info("Monthly growth needs two months of data and non-zero previous-month revenue.")
else:
    st.caption(
        f"Growth compares {kpis['growth_current_period']} "
        f"({format_currency(kpis['growth_current_revenue'])}) with "
        f"{kpis['growth_previous_period']} "
        f"({format_currency(kpis['growth_previous_revenue'])})."
    )

with st.expander("KPI formulas and business meaning", expanded=True):
    st.dataframe(pd.DataFrame(KPI_DEFINITIONS), use_container_width=True, hide_index=True)
with st.expander("KPI results table"):
    st.dataframe(format_kpi_table(kpis_to_dataframe(kpis)), use_container_width=True, hide_index=True)

st.subheader("Save Analysis to SQLite")
if st.button("Save cleaned data and KPIs"):
    run_id = save_analysis_run(cleaned_data, kpis, uploaded_file.name)
    st.success(f"Analysis saved to `{DEFAULT_DATABASE_PATH.name}` with run ID `{run_id}`.")
if DEFAULT_DATABASE_PATH.exists():
    with st.expander("Stored KPI history"):
        st.dataframe(load_kpi_history(), use_container_width=True, hide_index=True)
