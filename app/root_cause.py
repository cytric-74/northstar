from __future__ import annotations

from typing import Any
import pandas as pd

def analyze_root_cause(data: pd.DataFrame, metric: str = "Revenue") -> dict[str, Any]:
    if metric not in ["Revenue", "Profit"]:
        raise ValueError("Root Cause Analysis is only supported for 'Revenue' or 'Profit'.")

    null_res = {
        "drop_detected": False,
        "metric": metric,
        "total_change": 0.0,
        "pct_change": 0.0,
        "current_month": None,
        "previous_month": None,
        "dimension_reports": {},
        "explanations": ["Insufficient data or missing columns to perform root cause analysis."],
    }

    if data.empty or "Date" not in data.columns or metric not in data.columns:
        return null_res

    df = data.dropna(subset=["Date", metric]).copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month_Period"] = df["Date"].dt.to_period("M")

    monthly = df.groupby("Month_Period")[metric].sum().sort_index()

    if len(monthly) < 2:
        return {
            "drop_detected": False,
            "metric": metric,
            "total_change": 0.0,
            "pct_change": 0.0,
            "current_month": str(monthly.index[-1]) if not monthly.empty else None,
            "previous_month": None,
            "dimension_reports": {},
            "explanations": ["At least two months of historical data are required to run Root Cause Analysis."],
        }

    current_month, previous_month = monthly.index[-1], monthly.index[-2]
    current_val, previous_val = float(monthly.iloc[-1]), float(monthly.iloc[-2])
    total_change = current_val - previous_val
    pct_change = (total_change / previous_val) * 100 if previous_val != 0 else 0.0

    if total_change >= 0:
        return {
            "drop_detected": False,
            "metric": metric,
            "total_change": total_change,
            "pct_change": pct_change,
            "current_month": str(current_month),
            "previous_month": str(previous_month),
            "dimension_reports": {},
            "explanations": [
                f"No decline detected! Overall {metric} increased by **{pct_change:.1f}%** "
                f"from {previous_month} to {current_month} (+${total_change:,.2f})."
            ],
        }

    total_drop = abs(total_change)
    dimensions = ["Category", "Product", "Customer_ID"]
    dimension_reports = {}
    explanations = [
        f"Overall {metric} declined by **{abs(pct_change):.1f}%** (-${total_drop:,.2f}) "
        f"from {previous_month} (${previous_val:,.2f}) to {current_month} (${current_val:,.2f})."
    ]

    for dim in dimensions:
        if dim not in df.columns:
            continue

        dim_data = df[df["Month_Period"].isin([previous_month, current_month])]
        dim_grouped = dim_data.groupby([dim, "Month_Period"])[metric].sum().unstack(fill_value=0.0)

        if previous_month not in dim_grouped.columns:
            dim_grouped[previous_month] = 0.0
        if current_month not in dim_grouped.columns:
            dim_grouped[current_month] = 0.0

        dim_grouped["Change"] = dim_grouped[current_month] - dim_grouped[previous_month]
        dim_grouped["Pct_Change"] = ((dim_grouped["Change"] / dim_grouped[previous_month]) * 100).replace([float("inf"), float("-inf")], 0.0).fillna(0.0)
        
        contributors = dim_grouped[dim_grouped["Change"] < 0].copy()
        if contributors.empty:
            continue

        contributors["Abs_Change"] = contributors["Change"].abs()
        contributors["Contribution_Pct"] = (contributors["Abs_Change"] / total_drop) * 100
        contributors = contributors.sort_values(by="Change", ascending=True)

        top_culprit = contributors.index[0]
        culprit_prev = contributors.loc[top_culprit, previous_month]
        culprit_curr = contributors.loc[top_culprit, current_month]
        culprit_drop = abs(contributors.loc[top_culprit, "Change"])
        culprit_pct = abs(contributors.loc[top_culprit, "Pct_Change"])
        contrib_pct = contributors.loc[top_culprit, "Contribution_Pct"]

        contributors.columns = [str(col) for col in contributors.columns]
        dimension_reports[dim] = contributors.reset_index()

        display_name = f"Customer '{top_culprit}'" if dim == "Customer_ID" else str(top_culprit)
        explanations.append(
            f"Within **{dim}**, the largest drag was **{display_name}**. "
            f"Its {metric} sales fell from ${culprit_prev:,.2f} to ${culprit_curr:,.2f} (a **{culprit_pct:.1f}%** drop), "
            f"which alone explains **{contrib_pct:.1f}%** of the overall company-wide decline."
        )

    return {
        "drop_detected": True,
        "metric": metric,
        "total_change": total_change,
        "pct_change": pct_change,
        "current_month": str(current_month),
        "previous_month": str(previous_month),
        "dimension_reports": {
            dim: df_report.to_dict("records") for dim, df_report in dimension_reports.items()
        },
        "explanations": explanations,
    }
