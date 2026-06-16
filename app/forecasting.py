"""Forecasting Engine for projecting future sales using Moving Average and Linear Regression."""

from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd


def generate_forecast(
    data: pd.DataFrame,
    horizon_days: int = 30,
) -> dict[str, Any]:
    """Generate daily sales forecasts using Moving Average and Linear Regression."""
    if data.empty or "Date" not in data.columns or "Revenue" not in data.columns:
        return {
            "forecast_df": pd.DataFrame(),
            "metrics": {},
            "explanations": ["Insufficient data or missing columns to run forecast models."],
        }

    # Clean and aggregate daily sales
    df = data.dropna(subset=["Date", "Revenue"]).copy()
    df["Date"] = pd.to_datetime(df["Date"])
    daily = df.groupby("Date")["Revenue"].sum().sort_index()

    if len(daily) < 5:
        return {
            "forecast_df": pd.DataFrame(),
            "metrics": {},
            "explanations": ["At least 5 unique days of historical sales are required to generate forecasts."],
        }

    # Reindex to include all dates between min and max to fill in 0-revenue days
    full_idx = pd.date_range(start=daily.index.min(), end=daily.index.max(), freq="D")
    daily = daily.reindex(full_idx, fill_value=0.0)
    history_len = len(daily)

    # 1. Linear Regression (y = m * x + c)
    x = np.arange(history_len)
    y = daily.values

    # Fit linear regression model: y = m*x + c
    slope, intercept = np.polyfit(x, y, 1)

    # Generate dates for forecast horizon
    future_dates = pd.date_range(
        start=daily.index.max() + pd.Timedelta(days=1),
        periods=horizon_days,
        freq="D",
    )

    x_future = np.arange(history_len, history_len + horizon_days)
    lr_forecast = slope * x_future + intercept
    # Make sure we don't predict negative sales
    lr_forecast = np.clip(lr_forecast, 0, None)

    # 2. Moving Average Forecast (Rolling Auto-Regressive)
    # Use a 7-day window or 30-day window depending on history size
    window = 14 if history_len >= 14 else 7
    ma_history = list(y)
    ma_forecast = []

    for _ in range(horizon_days):
        next_ma = np.mean(ma_history[-window:])
        ma_forecast.append(next_ma)
        ma_history.append(next_ma)

    # Combine historical and forecasted data into a single DataFrame for graphing
    history_df = pd.DataFrame(
        {
            "Date": daily.index,
            "Actual_Revenue": y,
            "Forecast_MA": np.nan,
            "Forecast_LR": np.nan,
            "Type": "Historical",
        }
    )

    # Add a bridging row so the charts connect continuously from historical to forecast
    bridge_row = pd.DataFrame(
        {
            "Date": [daily.index[-1]],
            "Actual_Revenue": [y[-1]],
            "Forecast_MA": [y[-1]],
            "Forecast_LR": [y[-1]],
            "Type": ["Historical"],
        }
    )

    forecast_df = pd.DataFrame(
        {
            "Date": future_dates,
            "Actual_Revenue": np.nan,
            "Forecast_MA": ma_forecast,
            "Forecast_LR": lr_forecast,
            "Type": "Forecast",
        }
    )

    # Concatenate results
    result_df = pd.concat([history_df, bridge_row, forecast_df]).reset_index(drop=True)

    # Format explanations for beginner learning
    explanations = [
        "### 1. Moving Average (MA) Forecast Model\n\n"
        f"**Logic**: This model takes the average of the last **{window} days** of revenue to predict tomorrow's sales. "
        "To forecast multiple days out, we recursively feed the predicted values back into the average calculation.\n"
        "**Why it's useful**: It represents the 'current run rate' or status quo. It is excellent for stable businesses "
        "because it dampens short-term random noise, but it cannot capture structural upward or downward trends.\n"
        f"**Current 14-day Average Baseline**: ${np.mean(y[-window:]):,.2f} per day.\n",
        
        "### 2. Linear Regression (LR) Trend Model\n\n"
        "**Formula**: $y = m \\cdot x + c$\n"
        "- $y$: Predicted daily revenue\n"
        "- $x$: The day index (time elapsed)\n"
        f"- $m$ (Slope/Trend): **${slope:,.2f}/day** — this shows if your sales are trending up or down over time.\n"
        f"- $c$ (Y-Intercept): **${intercept:,.2f}**\n\n"
        "**Why it's useful**: Unlike the Moving Average, Linear Regression actively measures historical trajectory. "
        "If sales have been rising, it projects that growth forward. If they are falling, it warns you by sloping downward."
    ]

    metrics = {
        "slope": float(slope),
        "intercept": float(intercept),
        "average_historical_daily": float(np.mean(y)),
        "horizon_total_ma": float(np.sum(ma_forecast)),
        "horizon_total_lr": float(np.sum(lr_forecast)),
    }

    return {
        "forecast_df": result_df,
        "metrics": metrics,
        "explanations": explanations,
    }
