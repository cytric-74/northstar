from __future__ import annotations

from typing import Any
import numpy as np
import pandas as pd

def generate_forecast(
    data: pd.DataFrame,
    horizon_days: int = 30,
) -> dict[str, Any]:
    if horizon_days < 1:
        raise ValueError("Forecast horizon must be at least one day.")
    if data.empty or "Date" not in data.columns or "Revenue" not in data.columns:
        return {
            "forecast_df": pd.DataFrame(),
            "metrics": {},
            "explanations": ["Insufficient data or missing columns to run forecast models."],
        }

    df = data.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", format="mixed")
    df["Revenue"] = pd.to_numeric(df["Revenue"], errors="coerce")
    df = df.dropna(subset=["Date", "Revenue"])
    if df.empty:
        return {
            "forecast_df": pd.DataFrame(),
            "metrics": {},
            "explanations": ["No valid dated revenue rows are available to run forecast models."],
        }
    daily = df.groupby("Date")["Revenue"].sum().sort_index()

    if len(daily) < 5:
        return {
            "forecast_df": pd.DataFrame(),
            "metrics": {},
            "explanations": ["At least 5 unique days of historical sales are required to generate forecasts."],
        }

    full_idx = pd.date_range(start=daily.index.min(), end=daily.index.max(), freq="D")
    daily = daily.reindex(full_idx, fill_value=0.0)
    history_len = len(daily)

    x = np.arange(history_len)
    y = daily.values
    slope, intercept = np.polyfit(x, y, 1)
    fitted_history = slope * x + intercept
    residuals = y - fitted_history
    degrees_of_freedom = max(history_len - 2, 1)
    residual_standard_error = float(np.sqrt(np.sum(residuals ** 2) / degrees_of_freedom))
    x_centered_sum = float(np.sum((x - np.mean(x)) ** 2))

    future_dates = pd.date_range(
        start=daily.index.max() + pd.Timedelta(days=1),
        periods=horizon_days,
        freq="D",
    )

    x_future = np.arange(history_len, history_len + horizon_days)
    lr_forecast = np.clip(slope * x_future + intercept, 0, None)
    # 95% prediction intervals communicate both model residual noise and the
    # increasing uncertainty as the projection moves further from the data.
    if x_centered_sum > 0:
        prediction_se = residual_standard_error * np.sqrt(
            1 + (1 / history_len) + ((x_future - np.mean(x)) ** 2 / x_centered_sum)
        )
    else:
        prediction_se = np.full(horizon_days, residual_standard_error)
    confidence_margin = 1.96 * prediction_se
    lr_lower = np.clip(lr_forecast - confidence_margin, 0, None)
    lr_upper = lr_forecast + confidence_margin

    window = 14 if history_len >= 14 else 7
    ma_history = list(y)
    ma_forecast = []

    for _ in range(horizon_days):
        next_ma = np.mean(ma_history[-window:])
        ma_forecast.append(next_ma)
        ma_history.append(next_ma)

    history_df = pd.DataFrame(
        {
            "Date": daily.index,
            "Actual_Revenue": y,
            "Forecast_MA": np.nan,
            "Forecast_LR": np.nan,
            "Forecast_LR_Lower": np.nan,
            "Forecast_LR_Upper": np.nan,
            "Type": "Historical",
        }
    )

    bridge_row = pd.DataFrame(
        {
            "Date": [daily.index[-1]],
            "Actual_Revenue": [y[-1]],
            "Forecast_MA": [y[-1]],
            "Forecast_LR": [y[-1]],
            "Forecast_LR_Lower": [y[-1]],
            "Forecast_LR_Upper": [y[-1]],
            "Type": ["Historical"],
        }
    )

    forecast_df = pd.DataFrame(
        {
            "Date": future_dates,
            "Actual_Revenue": np.nan,
            "Forecast_MA": ma_forecast,
            "Forecast_LR": lr_forecast,
            "Forecast_LR_Lower": lr_lower,
            "Forecast_LR_Upper": lr_upper,
            "Type": "Forecast",
        }
    )

    result_df = pd.concat([history_df, bridge_row, forecast_df]).reset_index(drop=True)

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
        "residual_standard_error": residual_standard_error,
    }

    return {
        "forecast_df": result_df,
        "metrics": metrics,
        "explanations": explanations,
    }
