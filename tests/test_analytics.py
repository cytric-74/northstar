import sqlite3
from contextlib import closing
import pandas as pd
import pytest

from app.database import save_analysis_run
from app.kpi_engine import calculate_kpis
from app.sql_analytics import run_predefined_query, run_custom_query, PREDEFINED_QUERIES
from app.trend_analysis import calculate_trends
from app.root_cause import analyze_root_cause
from app.forecasting import generate_forecast
from app.recommendations import generate_recommendations


@pytest.fixture
def sample_sales_df():
    """Create a sample multi-month dataframe for testing analytical models."""
    return pd.DataFrame(
        {
            "Date": pd.to_datetime([
                "2026-01-01", "2026-01-15",
                "2026-02-01", "2026-02-15",
                "2026-03-01", "2026-03-15",
            ]),
            "Order_ID": ["O1", "O2", "O3", "O4", "O5", "O6"],
            "Customer_ID": ["C1", "C2", "C1", "C2", "C1", "C3"],
            "Product": ["Laptop", "Mouse", "Laptop", "Mouse", "Laptop", "Mouse"],
            "Category": ["Electronics", "Electronics", "Electronics", "Electronics", "Electronics", "Electronics"],
            "Revenue": [1000.0, 50.0, 800.0, 40.0, 900.0, 45.0],
            "Cost": [800.0, 30.0, 700.0, 25.0, 600.0, 20.0],
            "Profit": [200.0, 20.0, 100.0, 15.0, 300.0, 25.0],
            "Quantity": [1, 2, 1, 2, 1, 2],
        }
    )


def test_sql_analytics_engine(tmp_path, sample_sales_df):
    """Test SQL query executions against SQLite relational table."""
    db_path = tmp_path / "test_sql.db"
    kpis = calculate_kpis(sample_sales_df)
    run_id = save_analysis_run(sample_sales_df, kpis, "test.csv", db_path)

    # 1. Test predefined query execution
    df_products = run_predefined_query(run_id, "top_products", db_path)
    assert not df_products.empty
    assert "Product" in df_products.columns
    assert df_products.loc[0, "Product"] == "Laptop"
    assert df_products.loc[0, "Total_Revenue"] == 2700.0

    # 2. Test query descriptions and keys exist
    assert "top_categories" in PREDEFINED_QUERIES
    assert "worst_products" in PREDEFINED_QUERIES

    # 3. Test custom query execution
    custom_sql = "SELECT Product, SUM(Revenue) AS Revenue FROM sales_data WHERE run_id = :run_id GROUP BY Product"
    df_custom = run_custom_query(run_id, custom_sql, db_path)
    assert len(df_custom) == 2

    # 4. Test security blocks
    with pytest.raises(ValueError, match="SELECT"):
        run_custom_query(run_id, "INSERT INTO sales_data DEFAULT VALUES", db_path)

    with pytest.raises(ValueError, match="forbidden"):
        run_custom_query(run_id, "SELECT * FROM sales_data; DROP TABLE sales_data;", db_path)

    db_path.unlink()


def test_trend_analysis_growth_calculations(sample_sales_df):
    """Test growth period calculations and insights."""
    results = calculate_trends(sample_sales_df)

    assert not results["monthly_trends"].empty
    # January Rev: 1050, Feb Rev: 840 (drop of 20%), March Rev: 945 (increase of 12.5%)
    # Let's check that monthly indices exist in records
    monthly_rows = results["monthly_trends"]
    assert len(monthly_rows) == 3

    assert results["best_month"] == "2026-01"
    assert results["best_month_revenue"] == 1050.0
    assert results["worst_month"] == "2026-02"
    assert results["worst_month_revenue"] == 840.0
    assert len(results["insights"]) > 0


def test_root_cause_analysis_decline_isolation(sample_sales_df):
    """Test RCA engine correctly detects drops and isolates negative contributors."""
    # To test a drop, we use a dataset where revenue dropped from Jan to Feb
    jan_feb_df = sample_sales_df[sample_sales_df["Date"] < "2026-03-01"].copy()
    
    rca = analyze_root_cause(jan_feb_df, "Revenue")
    
    assert rca["drop_detected"] is True
    assert rca["total_change"] < 0
    assert rca["previous_month"] == "2026-01"
    assert rca["current_month"] == "2026-02"
    
    # Verify dimensions are captured
    reports = rca["dimension_reports"]
    assert "Product" in reports
    assert len(reports["Product"]) > 0
    
    # Laptop dropped from 1000 in Jan to 800 in Feb (-200)
    # Mouse dropped from 50 in Jan to 40 in Feb (-10)
    # So Laptop is the top culprit (largest negative change)
    top_prod = reports["Product"][0]
    assert top_prod["Product"] == "Laptop"
    assert top_prod["Change"] == -200.0


def test_forecasting_output_df(sample_sales_df):
    """Test linear regression and moving average forecasting shapes."""
    forecast = generate_forecast(sample_sales_df, horizon_days=10)
    
    df = forecast["forecast_df"]
    assert not df.empty
    assert len(df[df["Type"] == "Forecast"]) == 10
    assert "Forecast_MA" in df.columns
    assert "Forecast_LR" in df.columns
    assert forecast["metrics"]["horizon_total_ma"] > 0
    assert forecast["metrics"]["horizon_total_lr"] > 0


def test_business_recommendation_triggers(sample_sales_df):
    """Test rule-based heuristics trigger logical alerts."""
    kpis = {
        "revenue": 1000.0,
        "profit": 50.0,
        "profit_margin": 5.0,  # low margin
        "average_order_value": 500.0,
        "orders": 2,
        "customers": 2,
        "growth_rate": -10.0,
    }
    
    quality_summary = {
        "duplicate_rows_removed": 5,
        "invalid_dates_found": 1,
        "missing_values_before": 2,
    }
    
    recs = generate_recommendations(sample_sales_df, kpis, quality_summary)
    
    # Should trigger Low Margin alert
    assert any(r["title"] == "Conduct Urgent Cost & Pricing Review" for r in recs)
    # Should trigger duplicates alert
    assert any(r["title"] == "Audit Sales CSV Integration Script" for r in recs)
    # Should trigger invalid dates alert
    assert any(r["title"] == "Establish Clean Date Encoding Formats" for r in recs)
