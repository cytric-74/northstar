"""Programmatic generator for rich, realistic sales data to showcase KPI Analytics."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd


def generate_rich_sales_data(target_path: str | Path) -> None:
    """Generate a realistic, 6-month sales CSV with noise, duplicates, and KPI dips."""
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Setup seed for reproducible generation
    random.seed(42)

    # 1. Base configuration for products and categories
    products = {
        "Laptop": {"category": "Electronics", "price": 1200.0, "cost": 900.0},
        "Monitor": {"category": "Electronics", "price": 300.0, "cost": 180.0},
        "Headphones": {"category": "Electronics", "price": 150.0, "cost": 75.0},
        "Office Chair": {"category": "Furniture", "price": 250.0, "cost": 150.0},
        "Desk": {"category": "Furniture", "price": 450.0, "cost": 280.0},
        "Bookshelf": {"category": "Furniture", "price": 180.0, "cost": 110.0},
        "Sneakers": {"category": "Apparel", "price": 95.0, "cost": 50.0},
        "Hoodie": {"category": "Apparel", "price": 60.0, "cost": 30.0},
        "Backpack": {"category": "Apparel", "price": 45.0, "cost": 20.0},
    }

    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 6, 15)
    days = (end_date - start_date).days

    rows = []
    order_counter = 10000
    customer_list = [f"C-{random.randint(100, 999)}" for _ in range(120)]

    for day_offset in range(days + 1):
        current_date = start_date + timedelta(days=day_offset)
        # Determine day-of-week sales volume index (higher sales on weekends)
        is_weekend = current_date.weekday() >= 5
        num_orders = random.randint(3, 8) if is_weekend else random.randint(1, 5)

        # Engineer a specific "May drop" in Electronics sales
        # Electronics sales drop by 60% in May to showcase Root Cause Analysis
        may_electronics_slump = (current_date.month == 5)

        for _ in range(num_orders):
            order_counter += 1
            order_id = f"O-{order_counter}"
            customer_id = random.choice(customer_list)
            
            # Select 1 to 3 items per order
            num_items = random.randint(1, 3)
            for _ in range(num_items):
                prod_name = random.choice(list(products.keys()))
                prod_info = products[prod_name]
                
                # Apply the engineered dip for Electronics in May
                if may_electronics_slump and prod_info["category"] == "Electronics":
                    if random.random() < 0.65:
                        continue  # Skip order to create the dip

                quantity = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
                price = prod_info["price"]
                cost = prod_info["cost"]
                
                # Apply slight random pricing discount fluctuations
                discount = random.choices([0.0, 0.05, 0.1], weights=[0.8, 0.15, 0.05])[0]
                unit_price = price * (1 - discount)
                
                revenue = unit_price * quantity
                total_cost = cost * quantity
                profit = revenue - total_cost

                rows.append({
                    "Date": current_date.strftime("%Y-%m-%d"),
                    "Order_ID": order_id,
                    "Customer_ID": customer_id,
                    "Product": prod_name,
                    "Category": prod_info["category"],
                    "Revenue": round(revenue, 2),
                    "Cost": round(total_cost, 2),
                    "Profit": round(profit, 2),
                    "Quantity": quantity
                })

    df = pd.DataFrame(rows)

    # 2. Inject anomalies to test the Phase 1 cleaning functions
    # Inject 5 exact duplicate rows
    duplicates = df.sample(5, random_state=42).copy()
    df = pd.concat([df, duplicates], ignore_index=True)

    # Inject missing values (NaNs) in Cost and Profit
    df.loc[df.sample(frac=0.03, random_state=42).index, "Cost"] = None
    df.loc[df.sample(frac=0.02, random_state=10).index, "Profit"] = None

    # Inject missing values (NaNs) in Customer_ID
    df.loc[df.sample(frac=0.015, random_state=99).index, "Customer_ID"] = None

    # Inject invalid date formats
    date_indices = df.sample(3, random_state=77).index
    df.loc[date_indices, "Date"] = "CORRUPT_DATE"

    # Save to file
    df.to_csv(path, index=False)
