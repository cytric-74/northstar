# KPI Intelligence Platform

A high-performance portfolio project that turns uploaded sales transactional data into trustworthy business analysis, complete with data validation, KPI calculation pipelines, custom SQL sandbox, forecasting, root cause analytics, and recommendations.

## Core Features

- **Automated Data Cleaning**: Name normalization, duplicate row purging, date serialization, numeric imputation, and loss-leader detection.
- **KPI Metrics Engine**: Live calculation of Revenue, Net Profit, Profit Margin, Average Order Value, Unique Order count, Unique Customer count, and MoM Growth rate.
- **Relational SQL Playground**: Direct execution of queries against your upload session using SQLite. Runs on a secure, sandbox-isolated read-only connection.
- **Statistical Forecasting**: Daily sales projection using Moving Averages and Linear Regression models.
- **Drop Decomposition (RCA)**: Automatic analysis of Month-over-Month KPI drops to isolate culprit categories, products, or customers.
- **Business Alert Rules**: Automated heuristics warning about customer concentration, low margins, logistics vulnerabilities, and data logging bugs.

## Quick Start

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app/main.py
```

Run automated unit tests:
```powershell
python -m pytest
```

## Production Deployment & Containerization

### Environment Variables

| Variable | Description | Default |
| --- | --- | --- |
| `NORTHSTAR_DB_PATH` | Filepath to persistent SQLite file | `database/kpi_platform.db` |

### SQLite Production Setup

The platform uses SQLite optimized with **Write-Ahead Logging (WAL)** mode and `PRAGMA synchronous = NORMAL`. This maximizes read concurrency and prevents database write-locks in multi-user Streamlit deployments.

### Docker Deployment

To build and run as a lightweight container:

1. Create a `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8501
ENV NORTHSTAR_DB_PATH=/app/data/kpi_platform.db
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

2. Build and run the image:
```bash
docker build -t northstar-app .
docker run -p 8501:8501 -v /path/to/local/data:/app/data northstar-app
```
