from __future__ import annotations

from typing import Any
import pandas as pd

def calculate_trends(data: pd.DataFrame) -> dict[str, Any]:
    null_res = {
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
    if data.empty or "Date" not in data.columns or "Revenue" not in data.columns:
        return null_res

    df = data.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", format="mixed")
    df = df.dropna(subset=["Date"])
    if df.empty:
        return null_res

    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce").fillna(0)
    if "Profit" not in df.columns:
        df["Profit"] = 0.0
    else:
        df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce").fillna(0)
    df["Month_Period"] = df["Date"].dt.to_period("M")
    df["Quarter_Period"] = df["Date"].dt.to_period("Q")
    df["Year_Period"] = df["Date"].dt.to_period("Y")

    monthly = df.groupby("Month_Period")[["Revenue", "Profit"]].sum().sort_index()
    monthly["MoM_Revenue_Growth"] = monthly["Revenue"].pct_change() * 100
    monthly["MoM_Profit_Growth"] = monthly["Profit"].pct_change() * 100

    quarterly = df.groupby("Quarter_Period")[["Revenue", "Profit"]].sum().sort_index()
    quarterly["QoQ_Revenue_Growth"] = quarterly["Revenue"].pct_change() * 100
    quarterly["QoQ_Profit_Growth"] = quarterly["Profit"].pct_change() * 100

    yearly = df.groupby("Year_Period")[["Revenue", "Profit"]].sum().sort_index()
    yearly["YoY_Revenue_Growth"] = yearly["Revenue"].pct_change() * 100
    yearly["YoY_Profit_Growth"] = yearly["Profit"].pct_change() * 100

    best_month_period = monthly["Revenue"].idxmax() if not monthly.empty else None
    worst_month_period = monthly["Revenue"].idxmin() if not monthly.empty else None
    best_month = str(best_month_period) if best_month_period else None
    worst_month = str(worst_month_period) if worst_month_period else None
    best_month_revenue = float(monthly.loc[best_month_period, "Revenue"]) if best_month_period else 0.0
    worst_month_revenue = float(monthly.loc[worst_month_period, "Revenue"]) if worst_month_period else 0.0

    fastest_category, fastest_rate = None, None
    if len(monthly) >= 2 and "Category" in df.columns:
        latest_month = monthly.index[-1]
        previous_month = monthly.index[-2]
        cat_monthly = df.groupby(["Category", "Month_Period"])["Revenue"].sum().unstack(fill_value=0.0)
        if latest_month in cat_monthly.columns and previous_month in cat_monthly.columns:
            latest_revenues = cat_monthly[latest_month]
            prev_revenues = cat_monthly[previous_month]
            active_categories = prev_revenues[prev_revenues >= 10.0].index
            if not active_categories.empty:
                cat_growths = ((latest_revenues[active_categories] - prev_revenues[active_categories]) / prev_revenues[active_categories]) * 100
                if not cat_growths.empty and cat_growths.notna().any():
                    fastest_category = cat_growths.idxmax()
                    fastest_rate = float(cat_growths.max())

    insights = []
    if len(monthly) >= 2:
        latest_val, prev_val = monthly["Revenue"].iloc[-1], monthly["Revenue"].iloc[-2]
        if prev_val == 0:
            insights.append(
                f"Revenue was ${latest_val:,.2f} in the latest month ({monthly.index[-1]}). "
                f"A percentage comparison is unavailable because the previous month had zero revenue."
            )
        else:
            growth = ((latest_val - prev_val) / prev_val) * 100
            direction = "increased" if growth >= 0 else "decreased"
            insights.append(
                f"Revenue {direction} by {abs(growth):.1f}% in the latest month ({monthly.index[-1]}) "
                f"compared to the previous month ({monthly.index[-2]}) (${latest_val:,.2f} vs ${prev_val:,.2f})."
            )
        
        latest_profit, prev_profit = monthly["Profit"].iloc[-1], monthly["Profit"].iloc[-2]
        profit_growth = ((latest_profit - prev_profit) / prev_profit) * 100 if prev_profit != 0 else 0.0
        profit_dir = "increased" if profit_growth >= 0 else "decreased"
        insights.append(
            f"Net Profit {profit_dir} by {abs(profit_growth):.1f}% in the latest month "
            f"(${latest_profit:,.2f} vs ${prev_profit:,.2f})."
        )

    if len(quarterly) >= 2:
        latest_val, prev_val = quarterly["Revenue"].iloc[-1], quarterly["Revenue"].iloc[-2]
        if prev_val == 0:
            insights.append(
                f"Quarterly revenue was ${latest_val:,.2f} in {quarterly.index[-1]}; "
                "the previous quarter had zero revenue, so percentage growth is unavailable."
            )
        else:
            growth = ((latest_val - prev_val) / prev_val) * 100
            direction = "increased" if growth >= 0 else "decreased"
            insights.append(
                f"Quarterly Revenue {direction} by {abs(growth):.1f}% in {quarterly.index[-1]} "
                f"compared to {quarterly.index[-2]} (${latest_val:,.2f} vs ${prev_val:,.2f})."
            )

    if best_month:
        insights.append(f"Peak sales occurred in {best_month} with total revenue of ${best_month_revenue:,.2f}.")

    if fastest_category and fastest_rate is not None:
        insights.append(
            f"Fastest-growing category is **{fastest_category}** with a Month-over-Month growth rate of **{fastest_rate:.1f}%**."
        )

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
