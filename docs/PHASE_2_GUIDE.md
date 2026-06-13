# Phase 2 Guide: KPI Engine and SQLite Storage

## 1. What We Are Building

Phase 2 turns cleaned sales rows into reusable business metrics. It also stores
the cleaned data and KPI results in SQLite so the results persist after the
Streamlit session ends.

The application now calculates:

1. Revenue
2. Profit
3. Profit Margin
4. Average Order Value
5. Orders
6. Customers
7. Monthly Growth Rate

Phase 2 adds:

- `app/kpi_engine.py`: reusable KPI formulas.
- `app/database.py`: SQLite table creation, inserts, and KPI history queries.
- `tests/test_kpi_engine.py`: KPI calculation tests.
- `tests/test_database.py`: SQLite persistence test.
- A KPI and SQLite section in `app/main.py`.

## 2. Why KPIs Matter in Business

Raw transaction rows are too detailed for fast decisions. KPIs summarize those
rows into signals that leaders can monitor.

| KPI | Business Question |
|---|---|
| Revenue | How much did customers buy? |
| Profit | How much money remained after cost? |
| Profit Margin | How efficiently did revenue become profit? |
| Average Order Value | How much revenue does an average order generate? |
| Orders | How many distinct purchases occurred? |
| Customers | How many distinct customers purchased? |
| Monthly Growth Rate | Is recent revenue increasing or decreasing? |

Using reusable functions keeps the formulas consistent across Streamlit,
notebooks, SQL validation, Power BI, and future reports.

## 3. KPI Formulas

### Revenue

```text
Revenue = Sum of Revenue
```

For the cleaned sample data:

```text
Revenue = 1,200 + 450 + 300 + 375 + 700 + 200 + 150 = 3,375
```

### Profit

```text
Profit = Sum of Profit
```

### Profit Margin

```text
Profit Margin = (Profit / Revenue) x 100
```

A 30% margin means the business keeps 30 units of profit for every 100 units
of revenue.

### Average Order Value

```text
Average Order Value = Revenue / Distinct Orders
```

We count distinct `Order_ID` values because one order can contain multiple
product rows. Missing-value placeholders named `Unknown` are excluded.

### Orders

```text
Orders = Count of Distinct Order_ID
```

### Customers

```text
Customers = Count of Distinct Customer_ID
```

Missing-value placeholders named `Unknown` are excluded because they do not
represent a known customer.

### Monthly Growth Rate

```text
Monthly Growth Rate =
((Latest Month Revenue - Previous Month Revenue) / Previous Month Revenue) x 100
```

The engine uses the latest two calendar months present in the data. It returns
`N/A` when fewer than two months are available or previous-month revenue is
zero. Returning `N/A` is more honest than creating a misleading percentage.

## 4. SQLite Design

SQLite is a lightweight relational database stored in one local file:

```text
database/kpi_platform.db
```

The application creates three tables.

### `kpi_runs`

One row represents one click of the save button.

| Column | Meaning |
|---|---|
| `run_id` | Unique identifier for the saved analysis |
| `created_at` | UTC timestamp |
| `source_name` | Uploaded CSV filename |
| `row_count` | Number of cleaned sales rows |
| `growth_current_period` | Latest month used for growth |
| `growth_previous_period` | Comparison month |

### `kpi_results`

One row represents one KPI within a run. This long format makes it easy to add
new KPIs without adding a new database column every time.

| Column | Meaning |
|---|---|
| `run_id` | Links the KPI to `kpi_runs` |
| `kpi_name` | KPI name |
| `kpi_value` | Numeric KPI result |
| `unit` | `currency`, `percent`, or `count` |

### `cleaned_sales`

One row represents one cleaned sales record. The record is stored as JSON
during Phase 2 because uploaded files may contain optional extra columns such
as `Region`. Phase 3 will introduce a structured SQL sales table for analytics.

## 5. `app/kpi_engine.py` Walkthrough

### Configuration

- `REQUIRED_KPI_COLUMNS` lists the columns needed for all core KPIs.
- `KPI_DEFINITIONS` stores each formula and business meaning for display.

### Validation

- `validate_kpi_columns` compares required columns with uploaded columns.
- It raises a readable error listing missing columns.

### Individual KPI functions

- `calculate_revenue` sums `Revenue`.
- `calculate_profit` sums `Profit`.
- `calculate_profit_margin` divides profit by revenue and handles zero revenue.
- `_count_distinct_known` excludes null and `Unknown` placeholder IDs.
- `calculate_orders` counts distinct known order IDs.
- `calculate_customers` counts distinct known customer IDs.
- `calculate_average_order_value` divides revenue by distinct orders and
  handles zero orders.

Each formula has its own function so it can be tested and reused independently.

### Growth calculation

- `calculate_monthly_growth` first checks for a `Date` column.
- It removes rows without dates.
- `.dt.to_period("M")` converts each date to a calendar month.
- `groupby("Month")["Revenue"].sum()` calculates monthly revenue.
- The latest two months are selected.
- The percentage-change formula compares them.
- The function returns the rate, periods, and revenue values so the UI can
  explain the comparison.

### Combined results

- `calculate_kpis` validates the input and runs all KPI functions.
- It returns one dictionary containing the complete KPI snapshot.
- `kpis_to_dataframe` converts that dictionary into a long-format table.

## 6. `app/database.py` Walkthrough

### Database location

- `DEFAULT_DATABASE_PATH` builds an absolute path to
  `database/kpi_platform.db`.
- An absolute path ensures the database location does not change based on the
  terminal's current directory.

### Creating tables

- `initialize_database` creates the database folder if needed.
- `sqlite3.connect` opens or creates the database file.
- `CREATE TABLE IF NOT EXISTS` safely creates all three tables.
- Primary keys prevent duplicate identifiers.
- Foreign keys describe the relationship between a run and its records.

### Preparing sales records

- `_record_to_json` converts each DataFrame row into JSON.
- Missing values become JSON `null`.
- Pandas timestamps become `YYYY-MM-DD`.
- NumPy-style scalar values become regular Python values.

### Saving one analysis run

- `save_analysis_run` initializes the database.
- `uuid4()` creates a unique run ID.
- The current UTC timestamp records when the save occurred.
- The function inserts one run record.
- `executemany` inserts all KPI rows efficiently.
- A second `executemany` inserts all cleaned sales records.
- The transaction context commits all inserts together.
- `closing` explicitly releases each SQLite connection to prevent file locks.
- The function returns the run ID for confirmation.

### Loading history

- `load_kpi_history` joins `kpi_runs` and `kpi_results`.
- The query returns newest results first.
- `pd.read_sql_query` converts the SQL result into a DataFrame for Streamlit.

## 7. Streamlit Phase 2 Walkthrough

After Phase 1 cleans the uploaded file:

- `calculate_kpis(cleaned_data)` calculates the KPI snapshot.
- Two rows of `st.metric` cards show the headline results.
- A caption explains exactly which months monthly growth compares.
- The formulas expander explains each KPI.
- The results-table expander shows the KPI values and units.
- The save button calls `save_analysis_run`.
- The history expander reads saved KPI snapshots from SQLite.

Formatting functions change how numbers look in the UI but do not change the
underlying KPI values.

## 8. Tests

Run:

```powershell
python -m pytest
```

The Phase 2 tests verify:

- Revenue and profit sums.
- Profit margin.
- Distinct order and customer counts.
- Average order value.
- Monthly growth.
- Honest handling of a one-month dataset.
- Clear errors for missing required columns.
- SQLite run, KPI, and cleaned-sales inserts.
- KPI history queries.

## 9. How to Use Phase 2

Start the app:

```powershell
python -m streamlit run app/main.py
```

Then:

1. Upload `data/raw/sales_data.csv`.
2. Review the Phase 1 cleaning report.
3. Review the KPI cards and formulas.
4. Inspect the monthly-growth explanation.
5. Click **Save cleaned data and KPIs**.
6. Open **Stored KPI history**.

The database file is generated automatically and ignored by Git because it is
runtime output.

## 10. Phase 2 Completion Checklist

- [x] Revenue
- [x] Profit
- [x] Profit Margin
- [x] Average Order Value
- [x] Distinct Orders
- [x] Distinct Customers
- [x] Monthly Growth Rate
- [x] Reusable KPI functions
- [x] Formula explanations
- [x] SQLite tables
- [x] Cleaned-data persistence
- [x] KPI snapshot persistence
- [x] Stored KPI history
- [x] Automated tests

Stop here before Phase 3. Phase 3 will create structured SQL analytics tables
and beginner-friendly SQL queries.
