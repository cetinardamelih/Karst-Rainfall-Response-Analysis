from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def generate_synthetic_karst_data(
    start_date: str = "2022-01-01",
    periods: int = 365,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate daily synthetic rainfall, temperature, and spring discharge data.

    The discharge signal combines a slowly varying baseflow component with a
    lagged rainfall-response component. This is intentionally simple and meant
    for workflow testing, not physical hydrological modeling.
    """
    if periods < 30:
        raise ValueError("periods must be at least 30 days for meaningful lag analysis.")

    rng = np.random.default_rng(seed)
    dates = pd.date_range(start=start_date, periods=periods, freq="D")
    day_of_year = dates.dayofyear.to_numpy()

    seasonal_temperature = 14 + 10 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
    temperature_noise = rng.normal(0, 2.0, size=periods)
    temperature = seasonal_temperature + temperature_noise

    wet_season_factor = 0.55 + 0.45 * np.cos(2 * np.pi * (day_of_year - 15) / 365)
    rainy_day_probability = np.clip(0.18 + 0.28 * wet_season_factor, 0.08, 0.55)
    rainy_days = rng.random(periods) < rainy_day_probability
    rainfall = np.where(rainy_days, rng.gamma(shape=1.7, scale=8.0, size=periods), 0.0)

    event_indices = rng.choice(np.arange(20, periods - 10), size=max(4, periods // 120), replace=False)
    for idx in event_indices:
        rainfall[idx] += rng.uniform(35, 75)
        if idx + 1 < periods:
            rainfall[idx + 1] += rng.uniform(5, 25)

    baseflow = 1.15 + 0.18 * np.sin(2 * np.pi * (day_of_year + 35) / 365)
    baseflow += np.cumsum(rng.normal(0, 0.004, size=periods))
    baseflow = np.clip(baseflow, 0.75, None)

    response_kernel = np.array([0.02, 0.09, 0.20, 0.15, 0.08, 0.035, 0.015])
    rainfall_response = np.convolve(rainfall, response_kernel, mode="full")[:periods]
    discharge_noise = rng.normal(0, 0.06, size=periods)
    discharge = np.clip(baseflow + rainfall_response + discharge_noise, 0.05, None)

    return pd.DataFrame(
        {
            "date": dates,
            "rainfall_mm": np.round(rainfall, 2),
            "mean_temperature_C": np.round(temperature, 2),
            "spring_discharge_m3s": np.round(discharge, 3),
        }
    )


def save_synthetic_data(df: pd.DataFrame, output_path: Path) -> Path:
    """Save synthetic data as CSV and return the written path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
