from __future__ import annotations

import pandas as pd


def clean_timeseries(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and standardize the daily time series."""
    cleaned = df.copy()
    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned = cleaned.dropna(subset=["date"])
    cleaned = cleaned.sort_values("date").drop_duplicates(subset=["date"])

    numeric_columns = ["rainfall_mm", "mean_temperature_C", "spring_discharge_m3s"]
    for column in numeric_columns:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned["rainfall_mm"] = cleaned["rainfall_mm"].clip(lower=0)
    cleaned["spring_discharge_m3s"] = cleaned["spring_discharge_m3s"].clip(lower=0)
    cleaned[numeric_columns] = cleaned[numeric_columns].interpolate(limit_direction="both")

    return cleaned.reset_index(drop=True)


def add_lagged_rainfall(df: pd.DataFrame, max_lag_days: int = 14) -> pd.DataFrame:
    """Add rainfall lag columns for exploratory analysis."""
    if max_lag_days < 1:
        raise ValueError("max_lag_days must be at least 1.")

    enriched = df.copy()
    for lag in range(1, max_lag_days + 1):
        enriched[f"rainfall_lag_{lag}d_mm"] = enriched["rainfall_mm"].shift(lag)
    return enriched
