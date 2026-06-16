from __future__ import annotations

import sys
from pathlib import Path

# Add workspace directory to python search path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import sqlite3
from typing import Any
import pandas as pd
import streamlit as st

from app.data_quality import clean_sales_data, dataframe_to_csv_bytes
from app.database import DEFAULT_DATABASE_PATH, load_kpi_history, save_analysis_run
from app.kpi_engine import KPI_DEFINITIONS, calculate_kpis
from app.sample_generator import generate_rich_sales_data
from app.sql_analytics import run_predefined_query, run_custom_query, PREDEFINED_QUERIES
from app.trend_analysis import calculate_trends
from app.root_cause import analyze_root_cause
from app.forecasting import generate_forecast
from app.recommendations import generate_recommendations

st.set_page_config(
    page_title="Northstar",
    layout="wide",
    initial_sidebar_state="expanded",
)

SAMPLE_DATA_PATH = Path("data/raw/sales_data.csv")
if not SAMPLE_DATA_PATH.exists():
    generate_rich_sales_data(SAMPLE_DATA_PATH)

# Necto Mono inspired dark-mode stylesheets
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Roboto+Mono:wght@300;400;500;700&display=swap');
    
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0A0A0A !important;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: #F3F4F6 !important;
    }
    
    [data-testid="stHeader"] {
        background-color: rgba(10, 10, 10, 0.8) !important;
    }
    
    [data-testid="stSidebar"] {
        background-color: #0D0D0D !important;
        border-right: 1px solid #1E1E1E !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Roboto Mono', monospace !important;
        font-weight: 600 !important;
        letter-spacing: -0.5px !important;
    }
    
    .sidebar-logo {
        font-family: 'Roboto Mono', monospace;
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: 2px;
        color: #FFFFFF;
        padding: 10px 0;
        border-bottom: 1px solid #1E1E1E;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    .kpi-card {
        background-color: #121212 !important;
        border: 1px solid #1F1F1F !important;
        border-radius: 12px !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .kpi-card:hover {
        border-color: #d2ff3c !important;
        transform: translateY(-2px);
    }
    
    .kpi-card-title {
        font-family: 'Roboto Mono', monospace !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 1.5px !important;
        color: #8D8D8D !important;
        margin-bottom: 10px !important;
    }
    
    .kpi-card-value {
        font-family: 'Roboto Mono', monospace !important;
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #FFFFFF !important;
    }
    
    .kpi-card-growth {
        font-family: 'Roboto Mono', monospace !important;
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        margin-top: 8px !important;
    }
    
    .growth-up {
        color: #A3E635 !important;
    }
    
    .growth-down {
        color: #F87171 !important;
    }
    
    .badge-accent {
        background-color: #d2ff3c !important;
        color: #0A0A0A !important;
        font-family: 'Roboto Mono', monospace !important;
        font-weight: 700 !important;
        font-size: 0.7rem !important;
        padding: 3px 8px !important;
        border-radius: 9999px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        display: inline-block !important;
    }
    
    .badge-neutral {
        background-color: #1F1F1F !important;
        color: #CCCCCC !important;
        font-family: 'Roboto Mono', monospace !important;
        font-size: 0.7rem !important;
        padding: 3px 8px !important;
        border-radius: 9999px !important;
        text-transform: uppercase !important;
        display: inline-block;
        margin-right: 5px;
    }
    
    div[data-testid="stTable"] table {
        background-color: #121212 !important;
        border: 1px solid #1F1F1F !important;
        border-radius: 8px !important;
    }
    
    div.stButton > button {
        background-color: #FFFFFF !important;
        color: #0A0A0A !important;
        font-family: 'Roboto Mono', monospace !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: 1px solid #FFFFFF !important;
        padding: 8px 20px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }
    
    div.stButton > button:hover {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #FFFFFF !important;
    }
    
    code {
        font-family: 'Roboto Mono', monospace !important;
        background-color: #1A1A1A !important;
        color: #E2E8F0 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 4px !important;
        padding: 2px 6px !important;
    }
    
    .info-panel {
        background-color: #121212;
        border: 1px solid #1F1F1F;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def format_currency(value: float | None) -> str:
    return "N/A" if value is None or pd.isna(value) else f"${value:,.2f}"

def format_percent(value: float | None) -> str:
    return "N/A" if value is None or pd.isna(value) else f"{value:,.2f}%"

with st.sidebar:
    st.markdown(
        '<div class="sidebar-logo">NORTHSTAR</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div><span class="badge-neutral">v1.1</span>'
        '<span class="badge-accent">Professional</span></div>',
        unsafe_allow_html=True,
    )
    st.write("")
    
    menu = st.radio(
        "Navigation",
        [
            "Upload & Quality",
            "KPI Dashboard",
            "SQL Playground",
            "Trends & Root Cause",
            "Forecasting",
            "Recommendations",
            "Power BI Guide",
        ],
    )
    
    st.write("---")
    st.caption("cytric (github.com/cytric-74)")

if "raw_df" not in st.session_state:
    st.session_state["raw_df"] = None
if "cleaned_df" not in st.session_state:
    st.session_state["cleaned_df"] = None
if "quality_summary" not in st.session_state:
    st.session_state["quality_summary"] = None
if "column_report" not in st.session_state:
    st.session_state["column_report"] = None
if "actions_log" not in st.session_state:
    st.session_state["actions_log"] = []
if "kpis" not in st.session_state:
    st.session_state["kpis"] = None
if "source_name" not in st.session_state:
    st.session_state["source_name"] = ""
if "active_run_id" not in st.session_state:
    st.session_state["active_run_id"] = ""

# Auto-load synthetic data if nothing is loaded yet
if st.session_state["raw_df"] is None:
    try:
        synth_df = pd.read_csv(SAMPLE_DATA_PATH)
        cleaned, summary, col_rep, actions = clean_sales_data(synth_df)
        kpi_res = calculate_kpis(cleaned)
        
        st.session_state["raw_df"] = synth_df
        st.session_state["cleaned_df"] = cleaned
        st.session_state["quality_summary"] = summary
        st.session_state["column_report"] = col_rep
        st.session_state["actions_log"] = actions
        st.session_state["kpis"] = kpi_res
        st.session_state["source_name"] = "synthetic_sales_data.csv"
        
        run_id = save_analysis_run(cleaned, kpi_res, "synthetic_sales_data.csv")
        st.session_state["active_run_id"] = run_id
    except Exception as e:
        st.sidebar.error(f"Failed to auto-load sample data: {e}")

# --- Upload & Quality ---
if menu == "Upload & Quality":
    st.title("Data Upload & Quality Engine")
    st.write(
        "Upload your business transactions CSV. The platform will automatically map standard column names, "
        "impute missing financial records, resolve date stamps, and generate a quality health checklist."
    )

    uploaded_file = st.file_uploader("Upload sales data CSV", type=["csv"])
    
    if uploaded_file is not None:
        try:
            raw_data = pd.read_csv(uploaded_file)
            cleaned, summary, col_rep, actions = clean_sales_data(raw_data)
            kpis = calculate_kpis(cleaned)
            
            st.session_state["raw_df"] = raw_data
            st.session_state["cleaned_df"] = cleaned
            st.session_state["quality_summary"] = summary
            st.session_state["column_report"] = col_rep
            st.session_state["actions_log"] = actions
            st.session_state["kpis"] = kpis
            st.session_state["source_name"] = uploaded_file.name
            
            run_id = save_analysis_run(cleaned, kpis, uploaded_file.name)
            st.session_state["active_run_id"] = run_id
            st.success(f"Successfully processed and saved analysis run! ID: {run_id}")
        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.stop()

    summary = st.session_state["quality_summary"]
    cleaned_df = st.session_state["cleaned_df"]
    
    if summary and cleaned_df is not None:
        st.subheader("Data Quality Overview")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Initial Rows</div>
                    <div class="kpi-card-value">{summary['rows_before']:,}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Cleaned Rows</div>
                    <div class="kpi-card-value">{summary['rows_after']:,}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Duplicates Purged</div>
                    <div class="kpi-card-value">{summary['duplicate_rows_removed']:,}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Corrupt Dates Removed</div>
                    <div class="kpi-card-value">{summary['invalid_dates_found']:,}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col5:
            change = summary['quality_score_after'] - summary['quality_score_before']
            change_class = "growth-up" if change >= 0 else "growth-down"
            change_sign = "+" if change >= 0 else ""
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Quality Index</div>
                    <div class="kpi-card-value">{summary['quality_score_after']:.1f}%</div>
                    <div class="kpi-card-growth {change_class}">{change_sign}{change:.1f}% improvement</div>
                </div>""",
                unsafe_allow_html=True,
            )

        left, right = st.columns(2)
        with left:
            st.subheader("Cleaning Operations Log")
            st.markdown('<div class="info-panel">', unsafe_allow_html=True)
            for action in st.session_state["actions_log"]:
                st.markdown(f"- {action}")
            if not st.session_state["actions_log"]:
                st.markdown("- No cleaning operations were required. The uploaded CSV was pristine!")
            st.markdown('</div>', unsafe_allow_html=True)
            
        with right:
            st.subheader("Missing Fields Analysis")
            st.markdown('<div class="info-panel">', unsafe_allow_html=True)
            st.write(f"Total empty cells detected in raw file: **{summary['missing_values_before']:,}**")
            st.write(f"Remaining empty cells after imputation: **{summary['missing_values_after']:,}**")
            if summary["missing_expected_columns"]:
                st.warning("Missing optional columns: " + ", ".join(summary["missing_expected_columns"]))
            else:
                st.success("All expected schemas matched perfectly.")
            st.markdown('</div>', unsafe_allow_html=True)

        st.subheader("Column-Level Health Report")
        st.dataframe(st.session_state["column_report"], use_container_width=True, hide_index=True)

        st.subheader("Cleaned Dataset Sample (First 20 records)")
        st.dataframe(cleaned_df.head(20), use_container_width=True)
        
        st.download_button(
            "Download Cleaned Dataset CSV",
            dataframe_to_csv_bytes(cleaned_df),
            "cleaned_sales_dataset.csv",
            "text/csv",
        )

# --- KPI Dashboard ---
elif menu == "KPI Dashboard":
    st.title("Executive KPI Dashboard")
    st.write(
        "Standard financial performance indices. Hover over card values to see rounded accuracy figures, "
        "or expand the formulas guide to inspect calculation pipelines."
    )

    kpis = st.session_state["kpis"]
    
    if kpis:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Total Revenue</div>
                    <div class="kpi-card-value">{format_currency(kpis['revenue'])}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Total Net Profit</div>
                    <div class="kpi-card-value">{format_currency(kpis['profit'])}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Average Order Value</div>
                    <div class="kpi-card-value">{format_currency(kpis['average_order_value'])}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Profit Margin</div>
                    <div class="kpi-card-value">{format_percent(kpis['profit_margin'])}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        c5, c6, c7 = st.columns(3)
        with c5:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Total Orders</div>
                    <div class="kpi-card-value">{kpis['orders']:,}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c6:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Unique Customers</div>
                    <div class="kpi-card-value">{kpis['customers']:,}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c7:
            rate = kpis["growth_rate"]
            rate_class = "growth-up" if rate and rate >= 0 else "growth-down"
            rate_sign = "+" if rate and rate >= 0 else ""
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Monthly Growth Rate</div>
                    <div class="kpi-card-value">{format_percent(rate)}</div>
                    <div class="kpi-card-growth {rate_class}">{rate_sign}{format_percent(rate)} revenue delta</div>
                </div>""",
                unsafe_allow_html=True,
            )

        if rate is not None:
            st.info(
                f"Period Comparer: Latest month revenue of {format_currency(kpis['growth_current_revenue'])} "
                f"({kpis['growth_current_period']}) compared to previous month revenue of "
                f"{format_currency(kpis['growth_previous_revenue'])} ({kpis['growth_previous_period']})."
            )

        st.write("---")
        st.subheader("Calculations Formula Reference")
        st.dataframe(pd.DataFrame(KPI_DEFINITIONS), use_container_width=True, hide_index=True)

# --- SQL Playground ---
elif menu == "SQL Playground":
    st.title("Interactive SQL Playground")
    st.write(
        "A relational database playground running SQLite. Query your active uploaded sales records directly in real-time "
        "using standard ANSI SQL. Choose a pre-defined report to learn, or write a custom query!"
    )

    run_id = st.session_state["active_run_id"]
    if not run_id:
        st.warning("No database records available. Please upload a dataset in 'Upload & Quality' first.")
        st.stop()

    st.subheader("Run Predefined Analytical Reports")
    query_option = st.selectbox(
        "Select a report to analyze",
        list(PREDEFINED_QUERIES.keys()),
        format_func=lambda k: PREDEFINED_QUERIES[k]["title"],
    )

    report = PREDEFINED_QUERIES[query_option]
    st.write(f"*{report['description']}*")

    st.code(report["query"].replace(":run_id", f"'{run_id}'"), language="sql")

    try:
        res_df = run_predefined_query(run_id, query_option)
        st.dataframe(res_df, use_container_width=True)
    except Exception as e:
        st.error(f"SQL execution error: {e}")

    with st.expander("Learn SQL: Query Explanation"):
        st.markdown(report["explanation"])

    st.write("---")
    st.subheader("Interactive SQL Console")
    st.write(
        "Write custom queries against the database. The table containing your transactions is called sales_data. "
        "Columns available: Date, Order_ID, Customer_ID, Product, Category, Revenue, Cost, Profit, Quantity. "
        f"Always filter by run_id = '{run_id}' to isolate your dataset."
    )

    default_custom_sql = (
        "SELECT Product, COUNT(*) as Transaction_Count, SUM(Revenue) as Total_Revenue\n"
        "FROM sales_data\n"
        f"WHERE run_id = '{run_id}'\n"
        "GROUP BY Product\n"
        "ORDER BY Total_Revenue DESC"
    )

    custom_sql = st.text_area("Write SQL SELECT statement", value=default_custom_sql, height=180)
    
    if st.button("Execute Query"):
        try:
            custom_res = run_custom_query(run_id, custom_sql)
            st.success("Query executed successfully!")
            st.dataframe(custom_res, use_container_width=True)
        except Exception as e:
            st.error(f"SQL Execution Error: {e}")

# --- Trends & Root Cause ---
elif menu == "Trends & Root Cause":
    st.title("Trend & Root Cause Analysis")
    st.write(
        "Track corporate trajectory across calendar metrics and automatically dissect declines. "
        "The Root Cause Engine performs drop decomposition whenever revenue drops to pinpoint the exact category or customer leak."
    )

    cleaned_df = st.session_state["cleaned_df"]
    kpis = st.session_state["kpis"]

    if cleaned_df is not None:
        trends = calculate_trends(cleaned_df)
        
        st.subheader("Financial Trajectory Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Peak Sales Month</div>
                    <div class="kpi-card-value">{trends['best_month'] or 'N/A'}</div>
                    <div class="kpi-card-growth growth-up">Revenue: {format_currency(trends['best_month_revenue'])}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Lowest Sales Month</div>
                    <div class="kpi-card-value">{trends['worst_month'] or 'N/A'}</div>
                    <div class="kpi-card-growth growth-down">Revenue: {format_currency(trends['worst_month_revenue'])}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with col3:
            cat = trends["fastest_growing_category"]
            rate = trends["fastest_growing_category_rate"]
            rate_str = format_percent(rate)
            st.markdown(
                f"""<div class="kpi-card">
                    <div class="kpi-card-title">Fastest-Growing Division</div>
                    <div class="kpi-card-value">{cat or 'N/A'}</div>
                    <div class="kpi-card-growth growth-up">Growth: {rate_str} MoM</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.subheader("Revenue and Profit Timelines")
        mon_trends = trends["monthly_trends"]
        if not mon_trends.empty:
            chart_data = mon_trends.set_index("Month_Period")[["Revenue", "Profit"]]
            st.line_chart(chart_data, use_container_width=True)
        else:
            st.info("Insufficient monthly timelines to build charts.")

        st.write("---")
        st.subheader("Automated Root Cause Analysis (RCA)")
        
        selected_metric = st.selectbox("Select metric to analyze", ["Revenue", "Profit"])
        rca = analyze_root_cause(cleaned_df, selected_metric)

        st.markdown('<div class="info-panel">', unsafe_allow_html=True)
        st.write("### RCA Intelligence Report")
        for line in rca["explanations"]:
            st.write(line)
        st.markdown('</div>', unsafe_allow_html=True)

        if rca["drop_detected"]:
            st.write("### Decomposed Impact Breakdown")
            tab1, tab2, tab3 = st.tabs(["Category Impact", "Product Impact", "Customer Impact"])
            
            with tab1:
                if "Category" in rca["dimension_reports"]:
                    st.dataframe(pd.DataFrame(rca["dimension_reports"]["Category"]), use_container_width=True, hide_index=True)
            with tab2:
                if "Product" in rca["dimension_reports"]:
                    st.dataframe(pd.DataFrame(rca["dimension_reports"]["Product"]), use_container_width=True, hide_index=True)
            with tab3:
                if "Customer_ID" in rca["dimension_reports"]:
                    st.dataframe(pd.DataFrame(rca["dimension_reports"]["Customer_ID"]), use_container_width=True, hide_index=True)

# --- Forecasting ---
elif menu == "Forecasting":
    st.title("Predictive Sales Forecasting")
    st.write(
        "Project daily operational performance with statistical engines. Compare Moving Averages "
        "with Linear Regression trends over 30-day, 90-day, or 6-month horizons."
    )

    cleaned_df = st.session_state["cleaned_df"]
    if cleaned_df is not None:
        horizon = st.selectbox("Forecast Horizon", [30, 90, 180], format_func=lambda h: f"Next {h} Days")
        forecast = generate_forecast(cleaned_df, horizon)
        
        f_df = forecast["forecast_df"]
        metrics = forecast["metrics"]
        
        if not f_df.empty:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(
                    f"""<div class="kpi-card">
                        <div class="kpi-card-title">Average Daily Sales</div>
                        <div class="kpi-card-value">{format_currency(metrics['average_historical_daily'])}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"""<div class="kpi-card">
                        <div class="kpi-card-title">Projected Spend (Moving Avg)</div>
                        <div class="kpi-card-value">{format_currency(metrics['horizon_total_ma'])}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    f"""<div class="kpi-card">
                        <div class="kpi-card-title">Projected Spend (Linear Reg)</div>
                        <div class="kpi-card-value">{format_currency(metrics['horizon_total_lr'])}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            chart_df = f_df.set_index("Date")[["Actual_Revenue", "Forecast_MA", "Forecast_LR"]]
            st.subheader("Daily Sales Projections")
            st.line_chart(chart_df, use_container_width=True)
            
            st.write("---")
            st.subheader("How the Models Work")
            for explanation in forecast["explanations"]:
                st.markdown(explanation)
        else:
            st.info("Ensure you have at least 5 unique days of historical sales to generate forecasts.")

# --- Recommendations ---
elif menu == "Recommendations":
    st.title("Business Recommendation Engine")
    st.write(
        "Heuristic analysis recommendations compiled by cross-referencing KPI ratios, "
        "negative product margin lines, product seller distributions, and data collection sanitizers."
    )

    cleaned_df = st.session_state["cleaned_df"]
    kpis = st.session_state["kpis"]
    summary = st.session_state["quality_summary"]

    if cleaned_df is not None and kpis and summary:
        recs = generate_recommendations(cleaned_df, kpis, summary)
        
        if recs:
            for i, rec in enumerate(recs, 1):
                priority_color = (
                    "#EF4444" if rec["priority"] == "High"
                    else "#F59E0B" if rec["priority"] == "Medium"
                    else "#10B981"
                )
                
                st.markdown(
                    f"""
                    <div style="background-color: #121212; border-left: 5px solid {priority_color}; border-top: 1px solid #1F1F1F; border-right: 1px solid #1F1F1F; border-bottom: 1px solid #1F1F1F; border-radius: 8px; padding: 20px; margin-bottom: 15px;">
                        <span style="font-family: 'Roboto Mono', monospace; font-size: 0.7rem; font-weight: 700; color: {priority_color}; border: 1px solid {priority_color}; padding: 2px 6px; border-radius: 4px; text-transform: uppercase;">
                            {rec['priority']} PRIORITY
                        </span>
                        <span style="font-family: 'Roboto Mono', monospace; font-size: 0.7rem; color: #8D8D8D; margin-left: 10px;">
                            CATEGORY: {rec['category'].upper()}
                        </span>
                        <h4 style="margin: 12px 0 6px 0; color: #FFFFFF; font-family: 'Roboto Mono', monospace;">
                            {i}. {rec['title']}
                        </h4>
                        <p style="font-size: 0.85rem; color: #CCCCCC; margin-bottom: 10px;">
                            <strong>Trigger Alert:</strong> <em>{rec['trigger_reason']}</em>
                        </p>
                        <p style="font-size: 0.9rem; color: #F3F4F6; margin: 0; line-height: 1.4;">
                            {rec['description']}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("No business alerts triggered. The operational structure looks healthy.")
    else:
        st.warning("Upload dataset in 'Upload & Quality' first to run the recommendations engine.")

# --- Power BI Guide ---
elif menu == "Power BI Guide":
    st.title("Power BI Development Suite")
    st.write(
        "A structured roadmap to recreate this Northstar analytical platform within Microsoft Power BI, "
        "complete with relational diagrams, metric definitions, and copy-pasteable DAX scripts."
    )

    st.markdown(
        """
        ### 1. Relational Star Schema Model
        To build a robust data warehouse in Power BI, avoid import modeling from a single flat table. 
        Deconstruct your cleaned database into a Star Schema with one fact table and three dimension tables:
        
        *   **Fact_Sales**: `Order_ID`, `Date`, `Customer_ID`, `Product_ID`, `Revenue`, `Cost`, `Profit`, `Quantity`
        *   **Dim_Products**: `Product_ID`, `Product_Name`, `Category`
        *   **Dim_Customers**: `Customer_ID`
        *   **Dim_Calendar**: `Date`, `Year`, `Quarter`, `Month`, `Month_Name`, `Day_of_Week` (Mark as Date Table)
        
        **Relationships**:
        *   `Dim_Calendar[Date]` 1 --> * `Fact_Sales[Date]` (Active relationship)
        *   `Dim_Products[Product_ID]` 1 --> * `Fact_Sales[Product_ID]`
        *   `Dim_Customers[Customer_ID]` 1 --> * `Fact_Sales[Customer_ID]`
        
        ---
        
        ### 2. Core Business Measures (DAX)
        Create a dedicated, empty table in Power BI called `_Measures` and write the following DAX calculations:
        
        #### Total Revenue
        ```dax
        Total Revenue = SUM(Fact_Sales[Revenue])
        ```
        
        #### Total Cost
        ```dax
        Total Cost = SUM(Fact_Sales[Cost])
        ```
        
        #### Total Net Profit
        ```dax
        Total Profit = [Total Revenue] - [Total Cost]
        ```
        
        #### Profit Margin Percentage
        ```dax
        Profit Margin % = DIVIDE([Total Profit], [Total Revenue], 0)
        ```
        
        #### Total Orders (Distinct Count)
        ```dax
        Total Orders = DISTINCTCOUNT(Fact_Sales[Order_ID])
        ```
        
        #### Average Order Value (AOV)
        ```dax
        Average Order Value = DIVIDE([Total Revenue], [Total Orders], 0)
        ```
        
        #### Month-over-Month Revenue Growth Rate
        ```dax
        MoM Revenue Growth % = 
        VAR PriorMonthRevenue = 
            CALCULATE(
                [Total Revenue],
                DATEADD(Dim_Calendar[Date], -1, MONTH)
            )
        RETURN
            DIVIDE([Total Revenue] - PriorMonthRevenue, PriorMonthRevenue, 0)
        ```
        
        #### Year-to-Date (YTD) Revenue Running Total
        ```dax
        Revenue YTD = TOTALYTD([Total Revenue], Dim_Calendar[Date])
        ```
        
        ---
        
        ### 3. Visual Layout Guidelines
        *   **Typography**: Use Segoe UI Semibold for numbers and headings. Match font scaling to visual priority.
        *   **Color Theme**: Apply a dark dashboard layout. Set Canvas Background to `#0D0D0D` (0% transparency) and Visual Containers to `#161616` with a `12px` rounded border corner.
        *   **Visual Hierarchy**:
            *   *Top Row*: 4 KPI Card visuals representing **Revenue**, **Profit**, **Margin %**, and **AOV**.
            *   *Main Body (Left)*: Clustered column chart showing **Revenue by Category**.
            *   *Main Body (Right)*: Line chart showing **Total Revenue** and **Profit** mapped across `Dim_Calendar[Month]`.
            *   *Bottom Section*: Structured matrix table containing product sales breakdown.
        """
    )
