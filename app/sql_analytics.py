"""SQL Analytics Engine for executing queries against the SQLite database."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
import pandas as pd

from app.database import DEFAULT_DATABASE_PATH

PREDEFINED_QUERIES = {
    "top_products": {
        "title": "Top Products by Revenue",
        "description": "Identifies the highest revenue-generating products in the selected dataset.",
        "query": """
SELECT 
    Product, 
    SUM(Quantity) AS Total_Quantity, 
    SUM(Revenue) AS Total_Revenue, 
    SUM(Profit) AS Total_Profit
FROM sales_data
WHERE run_id = :run_id
GROUP BY Product
ORDER BY Total_Revenue DESC
LIMIT 5
        """,
        "explanation": (
            "1. **SELECT Product, SUM(Quantity) AS ...**: Selects product name and sums numeric columns to compute aggregate statistics.\n"
            "2. **FROM sales_data**: Points to our main relational transactions table.\n"
            "3. **WHERE run_id = :run_id**: Scopes the data to your specific uploaded dataset run.\n"
            "4. **GROUP BY Product**: Groups rows together by product name to compute aggregates per product.\n"
            "5. **ORDER BY Total_Revenue DESC**: Sorts products from highest revenue to lowest.\n"
            "6. **LIMIT 5**: Limits output to the top 5 records."
        ),
    },
    "top_categories": {
        "title": "Top Categories by Profit",
        "description": "Displays the product categories ordered by total profit generated.",
        "query": """
SELECT 
    Category, 
    SUM(Quantity) AS Total_Quantity, 
    SUM(Revenue) AS Total_Revenue, 
    SUM(Profit) AS Total_Profit
FROM sales_data
WHERE run_id = :run_id
GROUP BY Category
ORDER BY Total_Profit DESC
        """,
        "explanation": (
            "1. **GROUP BY Category**: Groups rows by product category (e.g., Electronics, Furniture).\n"
            "2. **SUM(Profit) AS Total_Profit**: Computes total net profit generated per product category.\n"
            "3. **ORDER BY Total_Profit DESC**: Sorts categories descending based on profit margins."
        ),
    },
    "monthly_revenue": {
        "title": "Monthly Revenue and Profit Trends",
        "description": "Calculates revenue and profit aggregated by calendar month to show performance trends.",
        "query": """
SELECT 
    strftime('%Y-%m', Date) AS Month, 
    SUM(Revenue) AS Total_Revenue, 
    SUM(Profit) AS Total_Profit
FROM sales_data
WHERE run_id = :run_id AND Date IS NOT NULL
GROUP BY Month
ORDER BY Month ASC
        """,
        "explanation": (
            "1. **strftime('%Y-%m', Date) AS Month**: Formats daily dates into year-month strings (e.g., '2026-01') to group transactions by calendar month.\n"
            "2. **GROUP BY Month**: Groups records by formatted month.\n"
            "3. **ORDER BY Month ASC**: Sorts results chronologically (oldest to newest) for charting."
        ),
    },
    "customer_segments": {
        "title": "Customer Segmentation (RFM Spend Profile)",
        "description": "Segments customers into VIP, Regular, or Occasional tiers based on their total transaction value.",
        "query": """
SELECT 
    Customer_ID,
    COUNT(DISTINCT Order_ID) AS Total_Orders,
    SUM(Revenue) AS Total_Spend,
    AVG(Revenue) AS Avg_Order_Value,
    CASE 
        WHEN SUM(Revenue) >= 15000 THEN 'VIP (Spend >= $15k)'
        WHEN SUM(Revenue) BETWEEN 3000 AND 14999 THEN 'Regular (Spend $3k - $15k)'
        ELSE 'Occasional (Spend < $3k)'
    END AS Customer_Segment
FROM sales_data
WHERE run_id = :run_id AND Customer_ID != 'Unknown'
GROUP BY Customer_ID
ORDER BY Total_Spend DESC
        """,
        "explanation": (
            "1. **COUNT(DISTINCT Order_ID)**: Counts unique order IDs to see transaction counts per customer.\n"
            "2. **SUM(Revenue)**: Aggregates total customer spend.\n"
            "3. **CASE WHEN ... THEN ... END**: Runs conditional logic to categorize customers into VIP, Regular, or Occasional spend brackets based on total spend.\n"
            "4. **ORDER BY Total_Spend DESC**: Ranks customers starting with the highest spenders."
        ),
    },
    "best_customers": {
        "title": "Best Customers by Total Spend",
        "description": "Lists the top 5 customer profiles by total revenue contribution.",
        "query": """
SELECT 
    Customer_ID, 
    COUNT(DISTINCT Order_ID) AS Orders, 
    SUM(Revenue) AS Total_Spend, 
    SUM(Profit) AS Total_Profit
FROM sales_data
WHERE run_id = :run_id AND Customer_ID != 'Unknown'
GROUP BY Customer_ID
ORDER BY Total_Spend DESC
LIMIT 5
        """,
        "explanation": (
            "1. **GROUP BY Customer_ID**: Aggregates metrics for each unique customer.\n"
            "2. **ORDER BY Total_Spend DESC LIMIT 5**: Selects the top 5 customers based on their historical spend."
        ),
    },
    "worst_products": {
        "title": "Worst Performing Products (Lowest Margins)",
        "description": "Identifies products with the lowest profit margin percentage. Low margins indicate high costs or pricing issues.",
        "query": """
SELECT 
    Product, 
    SUM(Revenue) AS Total_Revenue, 
    SUM(Profit) AS Total_Profit,
    CASE 
        WHEN SUM(Revenue) = 0 THEN 0 
        ELSE ROUND((SUM(Profit) / SUM(Revenue)) * 100, 2) 
    END AS Margin_Pct
FROM sales_data
WHERE run_id = :run_id
GROUP BY Product
ORDER BY Margin_Pct ASC
LIMIT 5
        """,
        "explanation": (
            "1. **SUM(Profit) / SUM(Revenue) * 100**: Computes the net profit margin percentage for each product.\n"
            "2. **CASE WHEN SUM(Revenue) = 0 THEN 0**: Handles division-by-zero if sales volume is zero.\n"
            "3. **ORDER BY Margin_Pct ASC LIMIT 5**: Identifies the 5 lowest-margin lines to focus audits."
        ),
    },
}

def run_predefined_query(
    run_id: str,
    query_key: str,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> pd.DataFrame:
    """Execute predefined analytical query."""
    if query_key not in PREDEFINED_QUERIES:
        raise ValueError(f"Unknown query key: {query_key}")

    query_str = PREDEFINED_QUERIES[query_key]["query"]
    with closing(sqlite3.connect(database_path)) as connection:
        return pd.read_sql_query(query_str, connection, params={"run_id": run_id})

def run_custom_query(
    run_id: str,
    custom_sql: str,
    database_path: str | Path = DEFAULT_DATABASE_PATH,
) -> pd.DataFrame:
    """Run safety-checked SELECT query against database."""
    cleaned_sql = custom_sql.strip()
    if not cleaned_sql.upper().startswith("SELECT"):
        raise ValueError("Security error: Only SELECT queries are allowed.")

    forbidden = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE"]
    for keyword in forbidden:
        if keyword in cleaned_sql.upper():
            raise ValueError(f"Security error: '{keyword}' is not allowed.")

    with closing(sqlite3.connect(database_path)) as connection:
        return pd.read_sql_query(cleaned_sql, connection, params={"run_id": run_id})
