"""Trend Analysis Engine for computing multi-period growth and generating text insights."""

from __future__ import annotations

from typing import Any
import pandas as pd


def calculate_trends(data: pd.DataFrame) -> dict[str, Any]:
    """Calculate growth rates, peaks, and generate business insights from sales data."""
    if data.empty or "Date" not in data.columns or "Revenue" not in data.columns:
        return {
            "monthly_trends": pd.DataFrame(),
            "quarterly_trends": pd.DataFrame(),
            "yearly_trends": pd.DataFrame(),
            "best_month": None,
            "worst_month": None,
            "best_month_revenue": 0.0,
            "worst_month_revenue": 0.0,
            "fastest_growing_category": None,
            "fastest_growing_category_rate": None,
            "insights": [],
        }

    df = data.dropna(subset=["Date"]).copy()
    if df.empty:
        return {
            "monthly_trends": pd.DataFrame(),
            "quarterly_trends": pd.DataFrame(),
            "yearly_trends": pd.DataFrame(),
            "best_month": None,
            "worst_month": None,
            "best_month_revenue": 0.0,
            "worst_month_revenue": 0.0,
            "fastest_growing_category": None,
            "fastest_growing_category_rate": None,
            "insights": [],
        }

    # Ensure Date is datetime type
    df["Date"] = pd.to_datetime(df["Date"])

    # 1. Monthly Trends
    df["Month_Period"] = df["Date"].dt.to_period("M")
    monthly = df.groupby("Month_Period")[["Revenue", "Profit"]].sum().sort_index()
    monthly["MoM_Revenue_Growth"] = monthly["Revenue"].pct_change() * 100
    monthly["MoM_Profit_Growth"] = monthly["Profit"].pct_change() * 100

    # 2. Quarterly Trends
    df["Quarter_Period"] = df["Date"].dt.to_period("Q")
    quarterly = df.groupby("Quarter_Period")[["Revenue", "Profit"]].sum().sort_index()
    quarterly["QoQ_Revenue_Growth"] = quarterly["Revenue"].pct_change() * 100
    quarterly["QoQ_Profit_Growth"] = quarterly["Profit"].pct_change() * 100

    # 3. Yearly Trends
    df["Year_Period"] = df["Date"].dt.to_period("Y")
    yearly = df.groupby("Year_Period")[["Revenue", "Profit"]].sum().sort_index()
    yearly["YoY_Revenue_Growth"] = yearly["Revenue"].pct_change() * 100
    yearly["YoY_Profit_Growth"] = yearly["Profit"].pct_change() * 100

    # 4. Best and Worst Month
    best_month_period = monthly["Revenue"].idxmax() if not monthly.empty else None
    worst_month_period = monthly["Revenue"].idxmin() if not monthly.empty else None
    best_month = str(best_month_period) if best_month_period else None
    worst_month = str(worst_month_period) if worst_month_period else None
    best_month_revenue = float(monthly.loc[best_month_period, "Revenue"]) if best_month_period else 0.0
    worst_month_revenue = float(monthly.loc[worst_month_period, "Revenue"]) if worst_month_period else 0.0

    # 5. Fastest Growing Category (based on latest month compared to previous)
    fastest_category = None
    fastest_rate = None

    if len(monthly) >= 2 and "Category" in df.columns:
        latest_month = monthly.index[-1]
        previous_month = monthly.index[-2]

        cat_monthly = df.groupby(["Category", "Month_Period"])["Revenue"].sum().unstack(fill_value=0.0)
        if latest_month in cat_monthly.columns and previous_month in cat_monthly.columns:
            latest_revenues = cat_monthly[latest_month]
            prev_revenues = cat_monthly[previous_month]

            # Filter out category with low volume baseline to avoid dividing by tiny numbers or zero
            active_categories = prev_revenues[prev_revenues >= 10.0].index
            if not active_categories.empty:
                cat_growths = (
                    (latest_revenues[active_categories] - prev_revenues[active_categories])
                    / prev_revenues[active_categories]
                ) * 100
                if not cat_growths.empty and cat_growths.notna().any():
                    fastest_category = cat_growths.idxmax()
                    fastest_rate = float(cat_growths.max())

    # 6. Generate Insights
    insights = []
    
    # MoM Insight
    if len(monthly) >= 2:
        latest_val = monthly["Revenue"].iloc[-1]
        prev_val = monthly["Revenue"].iloc[-2]
        growth = ((latest_val - prev_val) / prev_val) * 100
        direction = "increased" if growth >= 0 else "decreased"
        insights.append(
            f"Revenue {direction} by {abs(growth):.1f}% in the latest month ({monthly.index[-1]}) "
            f"compared to the previous month ({monthly.index[-2]}) (${latest_val:,.2f} vs ${prev_val:,.2f})."
        )
        
        # Profit Insight
        latest_profit = monthly["Profit"].iloc[-1]
        prev_profit = monthly["Profit"].iloc[-2]
        profit_growth = ((latest_profit - prev_profit) / prev_profit) * 100 if prev_profit != 0 else 0.0
        profit_dir = "increased" if profit_growth >= 0 else "decreased"
        insights.append(
            f"Net Profit {profit_dir} by {abs(profit_growth):.1f}% in the latest month "
            f"(${latest_profit:,.2f} vs ${prev_profit:,.2f})."
        )

    # QoQ Insight
    if len(quarterly) >= 2:
        latest_val = quarterly["Revenue"].iloc[-1]
        prev_val = quarterly["Revenue"].iloc[-2]
        growth = ((latest_val - prev_val) / prev_val) * 100
        direction = "increased" if growth >= 0 else "decreased"
        insights.append(
            f"Quarterly Revenue {direction} by {abs(growth):.1f}% in {quarterly.index[-1]} "
            f"compared to {quarterly.index[-2]} (${latest_val:,.2f} vs ${prev_val:,.2f})."
        )

    # Best Month Insight
    if best_month:
        insights.append(
            f"Peak sales occurred in {best_month} with total revenue of ${best_month_revenue:,.2f}."
        )

    # Fastest Growing Category Insight
    if fastest_category and fastest_rate is not None:
        direction = "expansion" if fastest_rate >= 0 else "contraction"
        insights.append(
            f"Fastest-growing category is **{fastest_category}** with a Month-over-Month growth rate of **{fastest_rate:.1f}%**."
        )

    # Convert Period indexes to strings for easy JSON serialization in UI
    monthly.index = monthly.index.astype(str)
    quarterly.index = quarterly.index.astype(str)
    yearly.index = yearly.index.astype(str)

    return {
        "monthly_trends": monthly.reset_index(),
        "quarterly_trends": quarterly.reset_index(),
        "yearly_trends": yearly.reset_index(),
        "best_month": best_month,
        "worst_month": worst_month,
        "best_month_revenue": best_month_revenue,
        "worst_month_revenue": worst_month_revenue,
        "fastest_growing_category": fastest_category,
        "fastest_growing_category_rate": fastest_rate,
        "insights": insights,
    }
