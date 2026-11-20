from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.data_loader import NUMERIC_COLUMNS

try:
    from scipy.signal import find_peaks as scipy_find_peaks
except ImportError:  # pragma: no cover - exercised only when scipy is absent.
    scipy_find_peaks = None


@dataclass(frozen=True)
class AnalysisSummary:
    """Compact summary of the rainfall-response analysis."""

    total_rainfall_mm: float
    mean_discharge_m3s: float
    max_discharge_m3s: float
    min_discharge_m3s: float
    rainfall_discharge_corr: float
    estimated_lag_days: int
    estimated_lag_corr: float
    rainfall_peak_count: int
    discharge_peak_count: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize summary fields as a plain dictionary."""
        return asdict(self)


def basic_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Return descriptive statistics for available numeric variables."""
    cols = [col for col in NUMERIC_COLUMNS if col in df.columns and df[col].notna().any()]
    return df[cols].describe().round(3)


def rainfall_discharge_correlation(df: pd.DataFrame) -> float:
    """Calculate same-day Pearson correlation between rainfall and discharge."""
    corr = df["rainfall_mm"].corr(df["spring_discharge_m3s"])
    return float(corr) if pd.notna(corr) else float("nan")


def lag_correlations(df: pd.DataFrame, max_lag_days: int = 14) -> pd.DataFrame:
    """Calculate Pearson correlations between lagged rainfall and spring discharge."""
    if max_lag_days < 0:
        raise ValueError("max_lag_days cannot be negative.")

    discharge = df["spring_discharge_m3s"]
    rainfall = df["rainfall_mm"]
    records = [
        {
            "lag_days": lag,
            "correlation": float(corr) if pd.notna(corr := rainfall.shift(lag).corr(discharge)) else np.nan,
        }
        for lag in range(max_lag_days + 1)
    ]
    return pd.DataFrame(records)


def estimate_lag_time(lag_corr_df: pd.DataFrame) -> tuple[int, float]:
    """Estimate response lag as the lag with maximum correlation."""
    valid = lag_corr_df.dropna(subset=["correlation"])
    if valid.empty:
        raise ValueError("No valid lag correlations available.")

    best_row = valid.loc[valid["correlation"].idxmax()]
    return int(best_row["lag_days"]), float(best_row["correlation"])


def find_rainfall_events(df: pd.DataFrame, percentile: float = 90.0) -> pd.DataFrame:
    """Find high rainfall events exceeding the given wet-day percentile threshold."""
    if not 0 < percentile < 100:
        raise ValueError("percentile must be between 0 and 100.")

    wet_days = df[df["rainfall_mm"] > 0]
    if wet_days.empty:
        return df.iloc[0:0][["date", "rainfall_mm", "spring_discharge_m3s"]].copy()

    threshold = float(np.percentile(wet_days["rainfall_mm"], percentile))
    events = df[df["rainfall_mm"] >= threshold].copy()
    return events[["date", "rainfall_mm", "spring_discharge_m3s"]].reset_index(drop=True)


def find_discharge_peaks(
    df: pd.DataFrame,
    prominence: float | None = None,
    distance_days: int = 3,
) -> pd.DataFrame:
    """Detect spring discharge peaks using scipy.signal.find_peaks (or fallback)."""
    if distance_days < 1:
        raise ValueError("distance_days must be at least 1.")

    discharge = df["spring_discharge_m3s"].to_numpy(dtype=float)
    if prominence is None:
        prominence = max(0.05, float(np.nanstd(discharge) * 0.8))

    if scipy_find_peaks is not None:
        peak_indices, properties = scipy_find_peaks(discharge, prominence=prominence, distance=distance_days)
    else:
        peak_indices, properties = _fallback_find_peaks(discharge, prominence, distance_days)

    peaks = df.iloc[peak_indices][["date", "rainfall_mm", "spring_discharge_m3s"]].copy()
    peaks["prominence"] = np.round(properties.get("prominences", np.array([])), 3)
    return peaks.reset_index(drop=True)


def build_analysis_summary(
    df: pd.DataFrame,
    max_lag_days: int = 14,
    rainfall_percentile: float = 90.0,
    discharge_prominence: float | None = None,
    peak_distance_days: int = 3,
) -> tuple[AnalysisSummary, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run core karst rainfall-response analyses and return summary + tables."""
    lag_df = lag_correlations(df, max_lag_days=max_lag_days)
    estimated_lag, estimated_corr = estimate_lag_time(lag_df)
    rainfall_events = find_rainfall_events(df, percentile=rainfall_percentile)
    discharge_peaks = find_discharge_peaks(
        df,
        prominence=discharge_prominence,
        distance_days=peak_distance_days,
    )

    summary = AnalysisSummary(
        total_rainfall_mm=float(df["rainfall_mm"].sum()),
        mean_discharge_m3s=float(df["spring_discharge_m3s"].mean()),
        max_discharge_m3s=float(df["spring_discharge_m3s"].max()),
        min_discharge_m3s=float(df["spring_discharge_m3s"].min()),
        rainfall_discharge_corr=rainfall_discharge_correlation(df),
        estimated_lag_days=estimated_lag,
        estimated_lag_corr=estimated_corr,
        rainfall_peak_count=int(len(rainfall_events)),
        discharge_peak_count=int(len(discharge_peaks)),
    )
    return summary, lag_df, rainfall_events, discharge_peaks


def _fallback_find_peaks(
    values: np.ndarray,
    prominence: float,
    distance_days: int,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Lightweight local peak finder used only when scipy is unavailable."""
    candidates: list[tuple[int, float]] = []
    for idx in range(1, len(values) - 1):
        if values[idx] > values[idx - 1] and values[idx] >= values[idx + 1]:
            local_prom = values[idx] - max(values[idx - 1], values[idx + 1])
            if local_prom >= prominence:
                candidates.append((idx, float(local_prom)))

    selected: list[tuple[int, float]] = []
    for idx, prom in sorted(candidates, key=lambda item: values[item[0]], reverse=True):
        if all(abs(idx - existing_idx) >= distance_days for existing_idx, _ in selected):
            selected.append((idx, prom))

    selected.sort(key=lambda item: item[0])
    peak_indices = np.array([idx for idx, _ in selected], dtype=int)
    prominences = np.array([prom for _, prom in selected], dtype=float)
    return peak_indices, {"prominences": prominences}
