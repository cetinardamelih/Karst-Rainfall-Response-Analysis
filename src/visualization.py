from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.ui_config import CHART_COLORS


def _prepare_output_path(output_dir: Path, filename: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / filename


def plot_rainfall_discharge_timeseries(df: pd.DataFrame, output_dir: Path) -> Path:
    """Plot rainfall bars and spring discharge time series."""
    path = _prepare_output_path(output_dir, "rainfall_discharge_timeseries.png")
    fig, ax_discharge = plt.subplots(figsize=(12, 6))
    ax_rain = ax_discharge.twinx()

    ax_rain.bar(df["date"], df["rainfall_mm"], color=CHART_COLORS["rainfall"], alpha=0.35, width=1.0, label="Rainfall")
    ax_rain.invert_yaxis()
    ax_rain.set_ylabel("Rainfall (mm/day)")

    ax_discharge.plot(df["date"], df["spring_discharge_m3s"], color=CHART_COLORS["discharge"], linewidth=1.8, label="Discharge")
    ax_discharge.set_ylabel("Spring discharge (m3/s)")
    ax_discharge.set_xlabel("Date")
    ax_discharge.set_title("Synthetic Karst Rainfall-Discharge Time Series")
    ax_discharge.grid(True, alpha=0.25)

    lines, labels = ax_discharge.get_legend_handles_labels()
    bars, bar_labels = ax_rain.get_legend_handles_labels()
    ax_discharge.legend(lines + bars, labels + bar_labels, loc="upper left")

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_rainfall_discharge_timeseries_log_y(df: pd.DataFrame, output_dir: Path) -> Path:
    """Plot rainfall bars and spring discharge time series with a log discharge axis."""
    path = _prepare_output_path(output_dir, "rainfall_discharge_timeseries_log_y.png")
    fig, ax_discharge = plt.subplots(figsize=(12, 6))
    ax_rain = ax_discharge.twinx()

    ax_rain.bar(df["date"], df["rainfall_mm"], color=CHART_COLORS["rainfall"], alpha=0.35, width=1.0, label="Rainfall")
    ax_rain.invert_yaxis()
    ax_rain.set_ylabel("Rainfall (mm/day)")

    discharge = df["spring_discharge_m3s"].where(df["spring_discharge_m3s"] > 0)
    ax_discharge.plot(df["date"], discharge, color=CHART_COLORS["discharge"], linewidth=1.8, label="Discharge")
    ax_discharge.set_yscale("log")
    ax_discharge.set_ylabel("Spring discharge (m3/s, log scale)")
    ax_discharge.set_xlabel("Date")
    ax_discharge.set_title("Synthetic Karst Rainfall-Discharge Time Series (Log Discharge Axis)")
    ax_discharge.grid(True, which="both", alpha=0.25)

    lines, labels = ax_discharge.get_legend_handles_labels()
    bars, bar_labels = ax_rain.get_legend_handles_labels()
    ax_discharge.legend(lines + bars, labels + bar_labels, loc="upper left")

    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_lag_correlation(lag_df: pd.DataFrame, output_dir: Path) -> Path:
    """Plot lagged rainfall-discharge correlations."""
    path = _prepare_output_path(output_dir, "lag_correlation.png")
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(lag_df["lag_days"], lag_df["correlation"], marker="o", color=CHART_COLORS["lag_correlation"])
    ax.axhline(0, color=CHART_COLORS["reference_line"], linewidth=0.8, alpha=0.5)
    ax.set_xlabel("Rainfall lag (days)")
    ax.set_ylabel("Pearson correlation")
    ax.set_title("Lagged Rainfall-Discharge Correlation")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_rainfall_discharge_scatter(df: pd.DataFrame, output_dir: Path) -> Path:
    """Plot same-day rainfall versus discharge."""
    path = _prepare_output_path(output_dir, "rainfall_discharge_scatter.png")
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(df["rainfall_mm"], df["spring_discharge_m3s"], alpha=0.65, color=CHART_COLORS["scatter_points"], edgecolor="white", linewidth=0.4)
    ax.set_xlabel("Rainfall (mm/day)")
    ax.set_ylabel("Spring discharge (m3/s)")
    ax.set_title("Rainfall-Discharge Scatter Plot")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_discharge_histogram(df: pd.DataFrame, output_dir: Path) -> Path:
    """Plot discharge distribution."""
    path = _prepare_output_path(output_dir, "discharge_histogram.png")
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hist(df["spring_discharge_m3s"], bins=30, color=CHART_COLORS["discharge"], edgecolor="white")
    ax.set_xlabel("Spring discharge (m3/s)")
    ax.set_ylabel("Frequency")
    ax.set_title("Spring Discharge Distribution")
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def create_all_figures(df: pd.DataFrame, lag_df: pd.DataFrame, output_dir: Path) -> list[Path]:
    """Create all MVP figures and return their paths."""
    return [
        plot_rainfall_discharge_timeseries(df, output_dir),
        plot_rainfall_discharge_timeseries_log_y(df, output_dir),
        plot_lag_correlation(lag_df, output_dir),
        plot_rainfall_discharge_scatter(df, output_dir),
        plot_discharge_histogram(df, output_dir),
    ]
