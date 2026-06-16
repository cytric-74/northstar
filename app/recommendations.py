"""Business Recommendation Engine providing rule-based actionable insights."""

from __future__ import annotations

from typing import Any
import pandas as pd


def generate_recommendations(
    data: pd.DataFrame,
    kpis: dict[str, Any],
    quality_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    """Analyze database records, KPI state, and quality alerts to output business advice."""
    recommendations = []

    if data.empty:
        return recommendations

    # 1. Company-wide Profit Margin Audit
    margin = kpis.get("profit_margin")
    if margin is not None and margin < 15.0:
        recommendations.append(
            {
                "title": "Conduct Urgent Cost & Pricing Review",
                "priority": "High" if margin < 5.0 else "Medium",
                "category": "Pricing & Strategy",
                "trigger_reason": f"Overall profit margin is currently low at {margin:.1f}%.",
                "description": (
                    "Your business is generating sales but keeping very little profit. "
                    "We recommend reviewing vendor costs for raw inventory, audit shipping expenses, "
                    "or raising prices on low-margin products by 3-5% to expand operational room."
                ),
            }
        )

    # 2. Product-level Profitability Audit (Loss Leaders)
    if {"Product", "Revenue", "Profit"}.issubset(data.columns):
        product_stats = data.groupby("Product")[["Revenue", "Profit"]].sum()
        product_stats["Margin_Pct"] = (
            product_stats["Profit"] / product_stats["Revenue"]
        ) * 100
        
        unprofitable = product_stats[product_stats["Profit"] < 0].sort_values(
            by="Profit"
        )
        for prod, row in unprofitable.head(2).iterrows():
            recommendations.append(
                {
                    "title": f"Review Cost Structure for Product: {prod}",
                    "priority": "High",
                    "category": "Pricing & Strategy",
                    "trigger_reason": f"Product '{prod}' operates at a net loss (Margin: {row['Margin_Pct']:.1f}%, Profit: -${abs(row['Profit']):,.2f}).",
                    "description": (
                        f"Every sale of {prod} is draining cash from the company. "
                        "Investigate if supplier rates have risen, check if this product is being "
                        "heavily discounted, or negotiate better manufacturing costs immediately."
                    ),
                }
            )

    # 3. High Volume Inventory Buffering
    if {"Product", "Revenue", "Quantity"}.issubset(data.columns):
        total_rev = kpis.get("revenue", 1.0)
        product_revs = data.groupby("Product")["Revenue"].sum()
        top_products = product_revs[product_revs / total_rev >= 0.20]  # Accounts for 20%+ of revenue
        
        for prod, rev in top_products.items():
            contrib = (rev / total_rev) * 100
            recommendations.append(
                {
                    "title": f"Increase Inventory Buffer for High-Seller: {prod}",
                    "priority": "Medium",
                    "category": "Inventory Management",
                    "trigger_reason": f"{prod} is a critical revenue driver representing {contrib:.1f}% of total sales.",
                    "description": (
                        f"Because {prod} represents a major share of your sales, running out of stock "
                        "would cause immediate and significant revenue loss. We recommend establishing "
                        "a higher safety stock threshold with your logistics team to prevent stockouts."
                    ),
                }
            )

    # 4. Customer Concentration Risk Analysis
    if {"Customer_ID", "Revenue"}.issubset(data.columns):
        total_rev = kpis.get("revenue", 1.0)
        customer_revs = data.groupby("Customer_ID")["Revenue"].sum().drop("Unknown", errors="ignore")
        
        if not customer_revs.empty:
            top_cust = customer_revs.idxmax()
            top_cust_rev = customer_revs.max()
            cust_contrib = (top_cust_rev / total_rev) * 100
            
            if cust_contrib >= 25.0:
                recommendations.append(
                    {
                        "title": f"Mitigate Customer Concentration Risk (Customer: {top_cust})",
                        "priority": "High" if cust_contrib >= 40.0 else "Medium",
                        "category": "Customer Relationship",
                        "trigger_reason": f"A single client represents {cust_contrib:.1f}% of total revenue.",
                        "description": (
                            f"Customer '{top_cust}' contributes ${top_cust_rev:,.2f} to your business. "
                            "If this customer leaves, it would cause a severe revenue contraction. "
                            "Recommend establishing an executive relationship, offering loyalty discounts, "
                            "and actively marketing to new segments to diversify your income stream."
                        ),
                    }
                )

    # 5. Data Integrity Audits (from Quality Report)
    duplicates = quality_summary.get("duplicate_rows_removed", 0)
    if duplicates > 0:
        recommendations.append(
            {
                "title": "Audit Sales CSV Integration Script",
                "priority": "Low",
                "category": "Data Operations",
                "trigger_reason": f"{duplicates} exact duplicate row(s) were automatically purged during upload.",
                "description": (
                    "Duplicate rows suggest that transactions are being written twice to the raw export file, "
                    "possibly due to database refresh issues or API double-post requests. Ask your data engineering team "
                    "to review the webhook logging script to ensure order IDs are unique at source."
                ),
            }
        )

    invalid_dates = quality_summary.get("invalid_dates_found", 0)
    if invalid_dates > 0:
        recommendations.append(
            {
                "title": "Establish Clean Date Encoding Formats",
                "priority": "Low",
                "category": "Data Operations",
                "trigger_reason": f"{invalid_dates} row(s) contained corrupt or unparseable dates.",
                "description": (
                    "Invalid date records had to be dropped to calculate accurate monthly growth metrics. "
                    "Verify if dates are entered manually by sales reps or if there are timezone encoding errors "
                    "in the export. Standardize all data collections to ISO-8601 (YYYY-MM-DD)."
                ),
            }
        )

    return recommendations
