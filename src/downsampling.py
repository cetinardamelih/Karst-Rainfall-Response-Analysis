from __future__ import annotations

import numpy as np
import pandas as pd


def lttb_indices(
    x: np.ndarray,
    y: np.ndarray,
    target_points: int,
    preserve_indices: np.ndarray | None = None,
) -> np.ndarray:
    """Select representative indices using Largest-Triangle-Three-Buckets (LTTB).

    Preserves the visual shape of long time series while optionally keeping
    critical hydrological peak indices untouched.
    """
    n = len(x)
    if target_points >= n or target_points < 3:
        return np.arange(n, dtype=int)

    # Replace NaNs temporarily with finite interpolated values for area calculation only.
    y_work = np.asarray(y, dtype=float)
    finite_mask = np.isfinite(y_work)
    if not finite_mask.any():
        return np.linspace(0, n - 1, target_points, dtype=int)
    if not finite_mask.all():
        valid_idx = np.flatnonzero(finite_mask)
        y_work = np.interp(np.arange(n), valid_idx, y_work[valid_idx])

    x_work = np.asarray(x, dtype=float)
    x_span = x_work[-1] - x_work[0]
    if x_span > 0:
        x_work = (x_work - x_work[0]) / x_span

    selected = np.empty(target_points, dtype=int)
    selected[0] = 0
    selected[-1] = n - 1

    bucket_size = (n - 2) / (target_points - 2)
    a_idx = 0

    for bucket in range(target_points - 2):
        range_start = int(np.floor(bucket * bucket_size)) + 1
        range_end = int(np.floor((bucket + 1) * bucket_size)) + 1
        range_end = min(range_end, n - 1)

        next_start = range_end
        next_end = int(np.floor((bucket + 2) * bucket_size)) + 1
        next_end = min(next_end, n)

        if next_start >= next_end:
            avg_x = x_work[n - 1]
            avg_y = y_work[n - 1]
        else:
            avg_x = float(np.mean(x_work[next_start:next_end]))
            avg_y = float(np.mean(y_work[next_start:next_end]))

        xs = x_work[range_start:range_end]
        ys = y_work[range_start:range_end]
        if len(xs) == 0:
            selected[bucket + 1] = a_idx
            continue

        ax_val = x_work[a_idx]
        ay_val = y_work[a_idx]
        areas = np.abs((ax_val - avg_x) * (ys - ay_val) - (ax_val - xs) * (avg_y - ay_val))
        best_offset = int(np.argmax(areas))
        a_idx = range_start + best_offset
        selected[bucket + 1] = a_idx

    if preserve_indices is not None and len(preserve_indices) > 0:
        valid_preserved = preserve_indices[(preserve_indices >= 0) & (preserve_indices < n)]
        selected = np.unique(np.concatenate([selected, valid_preserved]))
    else:
        selected = np.unique(selected)

    return selected


def downsample_timeseries(
    df: pd.DataFrame,
    date_col: str,
    value_col: str,
    threshold: int,
    target_points: int,
    preserve_dates: pd.Series | None = None,
) -> tuple[pd.DataFrame, bool]:
    """Apply peak-preserving LTTB downsampling when row count exceeds threshold."""
    if len(df) <= threshold or target_points >= len(df):
        return df, False

    x_numeric = df[date_col].astype("int64").to_numpy()
    y_values = df[value_col].to_numpy(dtype=float)

    preserve_idx: np.ndarray | None = None
    if preserve_dates is not None and len(preserve_dates) > 0:
        preserve_idx = np.flatnonzero(df[date_col].isin(preserve_dates).to_numpy())

    # Always keep the global max and min so the y-axis envelope never shrinks.
    extrema = []
    if np.isfinite(y_values).any():
        extrema.append(int(np.nanargmax(y_values)))
        extrema.append(int(np.nanargmin(y_values)))
    extrema_arr = np.array(extrema, dtype=int)
    if preserve_idx is not None and len(preserve_idx) > 0:
        preserve_idx = np.unique(np.concatenate([preserve_idx, extrema_arr]))
    else:
        preserve_idx = extrema_arr

    indices = lttb_indices(x_numeric, y_values, target_points=target_points, preserve_indices=preserve_idx)
    return df.iloc[indices].reset_index(drop=True), True


def build_webgl_rainfall_stems(
    dates: pd.Series,
    values: pd.Series,
    baseline: float = 0.0,
) -> tuple[list[pd.Timestamp | None], list[float | None]]:
    """Build None-separated vertical stem coordinates for fast WebGL Scattergl rainfall bars.

    Only non-zero rainfall days are emitted, avoiding thousands of SVG bar DOM nodes.
    """
    mask = values.notna() & (values > baseline)
    wet_dates = dates.loc[mask].tolist()
    wet_values = values.loc[mask].to_numpy(dtype=float)

    n = len(wet_dates)
    if n == 0:
        return [], []

    xs: list[pd.Timestamp | None] = [None] * (3 * n)
    ys: list[float | None] = [None] * (3 * n)
    for i, (dt, val) in enumerate(zip(wet_dates, wet_values)):
        base = 3 * i
        xs[base] = dt
        xs[base + 1] = dt
        ys[base] = baseline
        ys[base + 1] = float(val)
    return xs, ys
