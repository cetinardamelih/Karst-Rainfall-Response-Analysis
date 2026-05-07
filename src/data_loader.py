from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = {
    "date",
    "rainfall_mm",
    "mean_temperature_C",
    "spring_discharge_m3s",
}


def load_timeseries_csv(path: Path) -> pd.DataFrame:
    """Load a rainfall-discharge time series CSV with validated columns."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path, parse_dates=["date"])
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"CSV file is missing required columns: {missing_text}")

    return df.sort_values("date").reset_index(drop=True)


def save_processed_data(df: pd.DataFrame, path: Path) -> Path:
    """Save a processed time series CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
