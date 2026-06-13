# Phase 1 Guide: Data Upload and Data Quality

## 1. What We Are Building

In Phase 1, we are building the trustworthy input layer for the KPI
Intelligence Platform.

A user uploads a sales CSV. The application:

1. Reads the file.
2. Shows the original data.
3. Standardizes column names.
4. Removes exact duplicate rows.
5. converts dates and removes rows with unusable dates.
6. Converts numeric and currency values into numbers.
7. Handles missing values.
8. Generates a before-and-after data-quality report.
9. Lets the user download the cleaned data.

We are intentionally stopping after Phase 1. KPIs, SQLite, SQL, forecasting,
Power BI, and recommendations belong to later phases.

## 2. Why This Matters in Business

Business decisions are only as reliable as the input data.

- Duplicate orders can overstate revenue.
- Invalid dates can place sales in the wrong month or break trend analysis.
- Missing revenue or cost can make profit calculations inaccurate.
- Inconsistent column names make reusable analytics difficult.
- Missing product or customer names prevent useful grouping.

The quality report makes every automated change visible. This matters because
analysts should be able to explain how raw data became analysis-ready data.

## 3. Final Phase 1 Folder Structure

```text
KPI_Intelligence_Platform/
|
|-- app/
|   |-- __init__.py
|   |-- data_quality.py
|   `-- main.py
|-- dashboard/
|   `-- .gitkeep
|-- data/
|   |-- processed/
|   |   `-- .gitkeep
|   `-- raw/
|       `-- sales_data.csv
|-- database/
|   `-- .gitkeep
|-- docs/
|   `-- PHASE_1_GUIDE.md
|-- notebooks/
|   `-- .gitkeep
|-- reports/
|   `-- .gitkeep
|-- sql/
|   `-- .gitkeep
|-- tests/
|   `-- test_data_quality.py
|-- .gitignore
|-- README.md
`-- requirements.txt
```

The empty folders are placeholders for later phases:

- `sql/`: SQL query files.
- `notebooks/`: exploratory analysis.
- `dashboard/`: Power BI files and dashboard documentation.
- `database/`: SQLite database files.
- `reports/`: exported business reports.
- `data/processed/`: cleaned CSV outputs.

## 4. Setup From Zero

### Step 1: Open PowerShell in the project

```powershell
cd C:\Users\rohan\Desktop\northstar
```

`cd` changes the terminal's current directory. Commands now run inside the
project.

### Step 2: Create a virtual environment

```powershell
python -m venv venv
```

A virtual environment keeps this project's Python packages separate from other
projects.

### Step 3: Activate the virtual environment

```powershell
.\venv\Scripts\Activate.ps1
```

After activation, `python` and `pip` use the project's environment.

If PowerShell blocks the script, run this once in the current terminal:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the environment again.

### Step 4: Install dependencies

```powershell
python -m pip install -r requirements.txt
```

The dependency file contains:

- `pandas`: tables, CSV reading, cleaning, and reporting.
- `numpy`: included for later numerical phases.
- `streamlit`: the browser-based upload application.
- `pytest`: automated tests.

### Step 5: Start the application

```powershell
python -m streamlit run app/main.py
```

Streamlit prints a local URL, normally `http://localhost:8501`. Open it in a
browser and upload `data/raw/sales_data.csv`.

### Step 6: Run the tests

```powershell
python -m pytest
```

Tests confirm that duplicates, invalid dates, missing values, currency strings,
and CSV downloads behave as expected.

## 5. Cleaning Rules and Business Decisions

| Problem | Phase 1 Rule | Business Reason |
|---|---|---|
| Column naming differences | Match names without spaces, underscores, or capitalization | Makes later KPI functions reusable |
| Exact duplicate rows | Keep one copy | Prevents double-counting |
| Missing or invalid dates | Remove the row | A sale without a usable date cannot support reliable trends |
| Currency text such as `$1,200` | Remove `$` and `,`, then convert to a number | Enables arithmetic |
| Missing profit | Calculate `Revenue - Cost` when possible | Uses a defensible business formula |
| Other missing numeric values | Fill with the column median, or `0` if every value is missing | Median is less affected by extreme values |
| Missing text or IDs | Fill with `Unknown` | Preserves the transaction while clearly marking the gap |

These are starter rules, not universal rules. In a real company, an analyst
would confirm them with finance, sales operations, and data owners.

## 6. `app/data_quality.py` Walkthrough

This file is the reusable data-cleaning engine. Keeping it separate from the
Streamlit page means it can later be reused by notebooks, tests, scheduled
pipelines, and the KPI engine.

### Imports and configuration

- The module docstring explains the file's purpose.
- `from __future__ import annotations` makes type hints easier to use.
- `re` provides regular expressions for matching column-name variations.
- `Any` describes report values that can have multiple data types.
- `pandas as pd` provides the DataFrame operations.
- `EXPECTED_COLUMNS` lists the preferred sales schema.
- `NUMERIC_COLUMNS` identifies fields that need numeric conversion.
- `TEXT_COLUMNS` identifies fields where missing values become `Unknown`.

### `standardize_column_names`

- `data.copy()` protects the caller's original DataFrame.
- `expected_lookup` converts each expected name to a simplified key. For
  example, `Order_ID` becomes `orderid`.
- The loop simplifies each uploaded name in the same way.
- `rename` changes a matched name to the project's standard name.
- An unmatched column is preserved, so useful extra fields such as `Region`
  are not deleted.

### `_clean_numeric_series`

- `astype("string")` gives values consistent string behavior.
- `str.strip()` removes accidental spaces.
- `str.replace(r"[$,]", "", regex=True)` removes dollar signs and commas.
- Empty or textual null values become Pandas missing values.
- `pd.to_numeric(..., errors="coerce")` converts valid values and turns invalid
  values into missing values for later handling.

### `_quality_score`

- Empty data receives a score of `0`.
- Populated cells are counted with `notna()`.
- Total cells equal rows multiplied by columns.
- The score is the populated-cell percentage.

This is a simple completeness score. Future phases can add validity, accuracy,
timeliness, and consistency measures.

### `build_column_report`

- The function accepts the standardized data before cleaning and the final
  data after cleaning.
- It creates one report row per column.
- Each row records final data type, missing values before and after, and final
  unique-value count.
- The list of report rows becomes a DataFrame for display in Streamlit.

### `clean_sales_data`

- The function rejects an empty CSV because there is nothing to analyze.
- It standardizes names and creates a working copy.
- `duplicated().sum()` counts exact duplicate rows.
- `drop_duplicates()` removes those duplicates.
- Text values are trimmed and empty strings become missing values.
- The `Date` column is converted with invalid values set to missing.
- Rows with missing or invalid dates are removed.
- Numeric columns are converted one at a time.
- Missing `Profit` is calculated from `Revenue - Cost` when both columns exist.
- Remaining numeric gaps use the column median.
- Missing text values become `Unknown`.
- Data is sorted by date and row numbers are reset.
- Missing expected columns are reported but do not stop the app.
- The summary dictionary stores headline quality metrics.
- The function returns cleaned data, summary metrics, the column report, and
  plain-English cleaning actions.

### `dataframe_to_csv_bytes`

- A copy prevents export formatting from changing the displayed DataFrame.
- Dates are formatted as `YYYY-MM-DD`.
- `to_csv(index=False)` prevents Pandas row numbers from entering the file.
- UTF-8 bytes are returned because Streamlit's download button accepts bytes.

## 7. `app/main.py` Walkthrough

This file is the user interface.

### Page setup

- Pandas reads the uploaded CSV.
- Streamlit builds the browser interface.
- The cleaning functions are imported from `data_quality.py`.
- `st.set_page_config` sets the browser title and wide layout.
- `st.title`, `st.subheader`, and `st.write` explain the page.
- The expected-column expander helps users prepare their file.

### Upload and validation

- `st.file_uploader` only accepts CSV files.
- When no file exists, the page shows instructions and stops.
- `pd.read_csv` loads the upload into a DataFrame.
- The `try/except` block shows a readable error for malformed CSV files.
- The original data preview lets users verify what was uploaded.

### Cleaning and quality report

- `clean_sales_data(raw_data)` runs the reusable Phase 1 engine.
- Five `st.metric` cards show important headline results.
- The left column lists every cleaning action.
- The right column shows missing-value totals and missing expected columns.
- The column-level report gives detailed evidence.
- The cleaned preview lets users inspect the result.
- `st.download_button` exports the cleaned data.

## 8. Test Walkthrough

`tests/test_data_quality.py` creates a small DataFrame with:

- inconsistent column names,
- a bad date,
- a duplicate row,
- missing product and revenue,
- a currency-formatted revenue value,
- and missing profit.

The first test confirms that the cleaning output and report are correct. The
second test confirms that exported dates use the standard format.

## 9. How to Demonstrate Phase 1

1. Start the Streamlit app.
2. Upload the deliberately imperfect sample CSV.
3. Show the raw-data preview.
4. Explain the quality summary and each cleaning action.
5. Inspect the cleaned data.
6. Download the cleaned CSV.
7. Run `python -m pytest` to show that the logic is tested.

During an interview, explain the business tradeoff behind each cleaning rule.
The important point is not only that the data was cleaned, but that the rules
are transparent, reusable, and testable.

## 10. Phase 1 Completion Checklist

- [x] CSV upload
- [x] Automatic column-name standardization
- [x] Missing-value handling
- [x] Duplicate-row handling
- [x] Incorrect-date handling
- [x] Data-quality summary
- [x] Column-level quality report
- [x] Cleaned CSV download
- [x] Sample dirty dataset
- [x] Automated tests
- [x] Beginner setup and code explanation

Stop here before Phase 2. Phase 2 will introduce reusable KPI formulas and
SQLite storage only after Phase 1 is confirmed.
