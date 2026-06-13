import pandas as pd
import pytest

from app.kpi_engine import calculate_kpis, calculate_monthly_growth


def test_calculate_kpis_uses_distinct_orders_and_customers():
    data = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-02-01"]),
            "Order_ID": ["O-1", "O-1", "O-2"],
            "Customer_ID": ["C-1", "Unknown", "C-2"],
            "Revenue": [100, 50, 225],
            "Profit": [20, 10, 45],
        }
    )

    result = calculate_kpis(data)

    assert result["revenue"] == 375
    assert result["profit"] == 75
    assert result["profit_margin"] == 20
    assert result["average_order_value"] == 187.5
    assert result["orders"] == 2
    assert result["customers"] == 2
    assert result["growth_rate"] == 50
    assert result["growth_current_period"] == "2026-02"
    assert result["growth_previous_period"] == "2026-01"


def test_monthly_growth_is_unavailable_with_one_month():
    data = pd.DataFrame(
        {"Date": pd.to_datetime(["2026-01-01"]), "Revenue": [100]}
    )

    result = calculate_monthly_growth(data)

    assert result["growth_rate"] is None
    assert result["current_period"] == "2026-01"
    assert result["previous_period"] is None


def test_kpi_engine_reports_missing_required_columns():
    with pytest.raises(ValueError, match="Profit"):
        calculate_kpis(pd.DataFrame({"Revenue": [100]}))
