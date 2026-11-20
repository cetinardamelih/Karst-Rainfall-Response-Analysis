from __future__ import annotations

import numpy as np
import pandas as pd

from src.data_loader import NUMERIC_COLUMNS, STANDARD_COLUMNS


MISSING_METHODS: tuple[str, ...] = (
    "Linear interpolation",
    "Drop missing rows",
    "Forward fill",
)


def clean_timeseries(
    df: pd.DataFrame,
    missing_method: str = "Linear interpolation",
    trace_rain_threshold: float = 1.0,
) -> pd.DataFrame:
    """Clean, deduplicate, and standardize a daily karst time series."""
    if missing_method not in MISSING_METHODS:
        raise ValueError(f"Unsupported missing_method: {missing_method!r}. Expected one of {MISSING_METHODS}.")

    cleaned = df.copy()
    date_col = STANDARD_COLUMNS["date"]
    rain_col = STANDARD_COLUMNS["rainfall"]
    temp_col = STANDARD_COLUMNS["temperature"]
    discharge_col = STANDARD_COLUMNS["discharge"]

    cleaned[date_col] = pd.to_datetime(cleaned[date_col], errors="coerce")
    cleaned = cleaned.dropna(subset=[date_col])
    cleaned = cleaned.sort_values(date_col).drop_duplicates(subset=[date_col])

    for col in NUMERIC_COLUMNS:
        if col in cleaned.columns:
            cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")
        else:
            cleaned[col] = np.nan

    has_temperature = cleaned[temp_col].notna().any()
    active_numeric = [rain_col, discharge_col] + ([temp_col] if has_temperature else [])

    if missing_method == "Drop missing rows":
        cleaned = cleaned.dropna(subset=active_numeric)
    elif missing_method == "Forward fill":
        cleaned[active_numeric] = cleaned[active_numeric].ffill().bfill()
    else:  # Linear interpolation
        cleaned[active_numeric] = cleaned[active_numeric].interpolate(limit_direction="both")

    cleaned.loc[cleaned[rain_col] < trace_rain_threshold, rain_col] = 0.0
    cleaned[discharge_col] = cleaned[discharge_col].clip(lower=0.0)

    return cleaned.reset_index(drop=True)


def filter_date_range(
    df: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """Filter time series rows to an inclusive date range."""
    date_col = STANDARD_COLUMNS["date"]
    mask = (df[date_col] >= pd.to_datetime(start_date)) & (df[date_col] <= pd.to_datetime(end_date))
    return df.loc[mask].reset_index(drop=True)


def normalize_series(series: pd.Series) -> pd.Series:
    """Return min-max normalized values in [0, 1] with zero fallback for constant data."""
    min_val = series.min()
    max_val = series.max()
    if pd.isna(min_val) or pd.isna(max_val) or max_val == min_val:
        return pd.Series(np.zeros(len(series), dtype=float), index=series.index)
    return (series - min_val) / (max_val - min_val)


def positive_for_log(series: pd.Series) -> pd.Series:
    """Mask non-positive values as NaN so logarithmic y-axes stay valid."""
    return series.where(series > 0)
