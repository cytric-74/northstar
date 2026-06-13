# KPI Intelligence Platform

A portfolio project that turns uploaded sales data into trustworthy business
analysis. This repository currently contains **Phases 1 and 2**: data upload,
automatic cleaning, reusable KPI calculations, and SQLite persistence.

## Phase 1 Features

- Upload a CSV through Streamlit.
- Standardize common sales column names.
- Remove exact duplicate rows.
- validate dates and remove rows with unusable dates.
- Convert currency and numeric fields.
- Fill numeric gaps with the median.
- Calculate missing profit when revenue and cost are available.
- Label missing descriptive values as `Unknown`.
- Show a before-and-after quality report.
- Download the cleaned CSV.

## Phase 2 Features

- Calculate Revenue, Profit, Profit Margin, Average Order Value, Orders,
  Customers, and Monthly Growth Rate.
- Display formulas and business meanings.
- Use reusable, tested Python KPI functions.
- Save cleaned sales rows and timestamped KPI snapshots to SQLite.
- Review stored KPI history in Streamlit.

## Quick Start

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app/main.py
```

Open the local URL shown by Streamlit and upload
`data/raw/sales_data.csv`.

Run the automated tests:

```powershell
python -m pytest
```

## Beginner Guide

Read [docs/PHASE_1_GUIDE.md](docs/PHASE_1_GUIDE.md) for the complete setup,
business explanation, folder structure, cleaning logic, and code walkthrough.

Read [docs/PHASE_2_GUIDE.md](docs/PHASE_2_GUIDE.md) for KPI formulas, SQLite
design, code explanations, and Phase 2 verification.

Later phases will add SQL analytics, trend analysis, root-cause analysis,
forecasting, recommendations, Power BI, and the full multi-page Streamlit
application.
