from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


STANDARD_COLUMNS: dict[str, str] = {
    "date": "date",
    "rainfall": "rainfall_mm",
    "temperature": "mean_temperature_C",
    "discharge": "spring_discharge_m3s",
}

NUMERIC_COLUMNS: tuple[str, ...] = (
    STANDARD_COLUMNS["rainfall"],
    STANDARD_COLUMNS["temperature"],
    STANDARD_COLUMNS["discharge"],
)

REQUIRED_COLUMNS: set[str] = set(STANDARD_COLUMNS.values())


def load_timeseries_csv(path: Path) -> pd.DataFrame:
    """Load a rainfall-discharge time series CSV with validated columns."""
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    df = pd.read_csv(path, parse_dates=[STANDARD_COLUMNS["date"]])
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(f"CSV file is missing required columns: {missing_text}")

    return df.sort_values(STANDARD_COLUMNS["date"]).reset_index(drop=True)


def save_processed_data(df: pd.DataFrame, path: Path) -> Path:
    """Save a processed time series CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def infer_column(columns: list[str], candidates: list[str]) -> str | None:
    """Infer a likely column name from lower-case candidate substrings."""
    lowered = {col.lower(): col for col in columns}
    for candidate in candidates:
        for lower_name, original in lowered.items():
            if candidate in lower_name:
                return original
    return None


def map_input_columns(
    raw_df: pd.DataFrame,
    date_col: str,
    rainfall_col: str,
    discharge_col: str,
    temperature_col: str | None = None,
) -> pd.DataFrame:
    """Map arbitrary CSV columns to the standard internal schema."""
    mapped = pd.DataFrame(
        {
            STANDARD_COLUMNS["date"]: pd.to_datetime(raw_df[date_col], errors="coerce"),
            STANDARD_COLUMNS["rainfall"]: pd.to_numeric(raw_df[rainfall_col], errors="coerce"),
            STANDARD_COLUMNS["discharge"]: pd.to_numeric(raw_df[discharge_col], errors="coerce"),
        }
    )

    if temperature_col and temperature_col != "None" and temperature_col in raw_df.columns:
        mapped[STANDARD_COLUMNS["temperature"]] = pd.to_numeric(raw_df[temperature_col], errors="coerce")
    else:
        mapped[STANDARD_COLUMNS["temperature"]] = np.nan

    return mapped
