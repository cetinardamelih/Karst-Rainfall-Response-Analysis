from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from src.plot_config import (
    load_plot_config,
    mpl_legend_kwargs,
    mpl_linestyle,
    mpl_marker,
)
from src.preprocessing import positive_for_log


def _resolve_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return config if config is not None else load_plot_config()


def _save_figure(fig: plt.Figure, output_dir: Path, stem: str, config: dict[str, Any]) -> list[Path]:
    """Save a Matplotlib figure in all configured output formats and close it."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dpi = int(config["layout"]["dpi"])
    bg = config["colors"]["background"]
    formats = config["layout"].get("save_formats") or ["png"]

    saved: list[Path] = []
    fig.tight_layout()
    for fmt in formats:
        ext = str(fmt).lstrip(".").lower()
        path = output_dir / f"{stem}.{ext}"
        fig.savefig(path, dpi=dpi, facecolor=bg, bbox_inches="tight")
        saved.append(path)
    plt.close(fig)
    return saved


def _apply_axes_style(
    fig: plt.Figure,
    ax: plt.Axes,
    config: dict[str, Any],
    *,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    grid_axis: str = "both",
    grid_which: str = "major",
) -> None:
    """Apply centralized colors, typography, and grid settings to a Matplotlib axis."""
    colors = config["colors"]
    typo = config["typography"]
    layout = config["layout"]

    fig.patch.set_facecolor(colors["background"])
    ax.set_facecolor(colors["plot_background"])

    if title:
        ax.set_title(title, fontsize=typo["title_size"], color=colors["heading"], pad=10)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=typo["axis_label_size"], color=colors["text"])
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=typo["axis_label_size"], color=colors["text"])

    ax.tick_params(axis="both", labelsize=typo["tick_size"], colors=colors["text"])
    for spine in ax.spines.values():
        spine.set_color(colors["grid"])

    if layout["show_grid"]:
        ax.grid(
            True,
            which=grid_which,
            axis=grid_axis,
            color=colors["grid"],
            alpha=layout["grid_alpha"],
            linestyle=mpl_linestyle(layout["grid_linestyle"]),
            linewidth=layout["grid_linewidth"],
        )
    else:
        ax.grid(False)


def _style_secondary_axis(ax: plt.Axes, config: dict[str, Any], ylabel: str) -> None:
    colors = config["colors"]
    typo = config["typography"]
    ax.set_ylabel(ylabel, fontsize=typo["axis_label_size"], color=colors["text"])
    ax.tick_params(axis="y", labelsize=typo["tick_size"], colors=colors["text"])
    for spine in ax.spines.values():
        spine.set_color(colors["grid"])


def _plot_rainfall_on_axis(ax_rain: plt.Axes, dates: pd.Series, rainfall: pd.Series, config: dict[str, Any]) -> None:
    colors = config["colors"]
    styles = config["styles"]
    labels = config["layout"]["labels"]

    if styles["rainfall_display"] == "line":
        ax_rain.plot(
            dates,
            rainfall,
            color=colors["rainfall"],
            linewidth=styles["rainfall_linewidth"],
            linestyle=mpl_linestyle(styles["rainfall_linestyle"]),
            alpha=styles["rainfall_alpha"],
            label=labels["series_rainfall"],
        )
    else:
        ax_rain.bar(
            dates,
            rainfall,
            color=colors["rainfall"],
            alpha=styles["rainfall_alpha"],
            width=styles["rainfall_bar_width"],
            label=labels["series_rainfall"],
        )
    ax_rain.invert_yaxis()


def _plot_timeseries_core(
    df: pd.DataFrame,
    output_dir: Path,
    stem: str,
    config: dict[str, Any],
    *,
    log_y: bool = False,
    title_key: str = "timeseries_title",
    rainfall_events: pd.DataFrame | None = None,
    discharge_peaks: pd.DataFrame | None = None,
    show_peaks: bool = False,
) -> list[Path]:
    """Shared Matplotlib builder for linear, log-Y, and peak-annotated time series."""
    colors = config["colors"]
    styles = config["styles"]
    typo = config["typography"]
    layout = config["layout"]
    labels = layout["labels"]

    show_temp = (
        bool(layout["show_temperature"])
        and "mean_temperature_C" in df.columns
        and df["mean_temperature_C"].notna().any()
    )
    figsize = tuple(layout["figsize_timeseries"])

    with plt.rc_context({"font.family": typo["font_family"]}):
        if show_temp:
            fig, (ax_discharge, ax_temp) = plt.subplots(
                2,
                1,
                figsize=(figsize[0], figsize[1] * 1.25),
                sharex=True,
                gridspec_kw={"height_ratios": [3, 1]},
            )
        else:
            fig, ax_discharge = plt.subplots(figsize=figsize)
            ax_temp = None

        ax_rain = ax_discharge.twinx()
        _plot_rainfall_on_axis(ax_rain, df["date"], df["rainfall_mm"], config)
        _style_secondary_axis(ax_rain, config, labels["rainfall_axis"])

        discharge = positive_for_log(df["spring_discharge_m3s"]) if log_y else df["spring_discharge_m3s"]
        ax_discharge.plot(
            df["date"],
            discharge,
            color=colors["discharge"],
            linewidth=styles["discharge_linewidth"],
            linestyle=mpl_linestyle(styles["discharge_linestyle"]),
            alpha=styles["discharge_alpha"],
            label=labels["series_discharge"],
        )

        if show_peaks:
            if rainfall_events is not None and not rainfall_events.empty:
                ax_rain.scatter(
                    rainfall_events["date"],
                    rainfall_events["rainfall_mm"],
                    color=colors["rainfall_peak"],
                    marker=mpl_marker(styles["rainfall_peak_marker"]),
                    s=styles["rainfall_peak_marker_size"] ** 2,
                    alpha=styles["rainfall_peak_alpha"],
                    edgecolors=colors["marker_edge"],
                    linewidths=styles["scatter_edge_width"],
                    zorder=5,
                    label=labels["series_rainfall_peaks"],
                )
            if discharge_peaks is not None and not discharge_peaks.empty:
                peak_y = (
                    positive_for_log(discharge_peaks["spring_discharge_m3s"])
                    if log_y
                    else discharge_peaks["spring_discharge_m3s"]
                )
                ax_discharge.scatter(
                    discharge_peaks["date"],
                    peak_y,
                    color=colors["discharge_peak"],
                    marker=mpl_marker(styles["discharge_peak_marker"]),
                    s=styles["discharge_peak_marker_size"] ** 2,
                    alpha=styles["discharge_peak_alpha"],
                    edgecolors=colors["marker_edge"],
                    linewidths=styles["scatter_edge_width"],
                    zorder=5,
                    label=labels["series_discharge_peaks"],
                )

        if log_y:
            ax_discharge.set_yscale("log")

        _apply_axes_style(
            fig,
            ax_discharge,
            config,
            title=labels[title_key],
            xlabel=None if show_temp else labels["date_axis"],
            ylabel=labels["discharge_log_axis"] if log_y else labels["discharge_axis"],
            grid_which="both" if log_y else "major",
        )

        if layout["show_legend"]:
            handles_d, labels_d = ax_discharge.get_legend_handles_labels()
            handles_r, labels_r = ax_rain.get_legend_handles_labels()
            ax_discharge.legend(handles_d + handles_r, labels_d + labels_r, **mpl_legend_kwargs(config))

        if ax_temp is not None:
            ax_temp.plot(
                df["date"],
                df["mean_temperature_C"],
                color=colors["temperature"],
                linewidth=styles["temperature_linewidth"],
                linestyle=mpl_linestyle(styles["temperature_linestyle"]),
                alpha=styles["temperature_alpha"],
                label=labels["series_temperature"],
            )
            _apply_axes_style(
                fig,
                ax_temp,
                config,
                xlabel=labels["date_axis"],
                ylabel=labels["temperature_axis"],
            )
            if layout["show_legend"]:
                ax_temp.legend(**mpl_legend_kwargs(config))

        return _save_figure(fig, output_dir, stem, config)


def plot_rainfall_discharge_timeseries(
    df: pd.DataFrame,
    output_dir: Path,
    config: dict[str, Any] | None = None,
    rainfall_events: pd.DataFrame | None = None,
    discharge_peaks: pd.DataFrame | None = None,
) -> list[Path]:
    """Plot static rainfall-discharge time series."""
    cfg = _resolve_config(config)
    return _plot_timeseries_core(
        df,
        output_dir,
        "rainfall_discharge_timeseries",
        cfg,
        log_y=False,
        title_key="timeseries_title",
        rainfall_events=rainfall_events,
        discharge_peaks=discharge_peaks,
        show_peaks=bool(cfg["layout"]["show_peaks_on_timeseries"]),
    )


def plot_rainfall_discharge_timeseries_log_y(
    df: pd.DataFrame,
    output_dir: Path,
    config: dict[str, Any] | None = None,
    rainfall_events: pd.DataFrame | None = None,
    discharge_peaks: pd.DataFrame | None = None,
) -> list[Path]:
    """Plot static rainfall-discharge time series with a logarithmic discharge axis."""
    cfg = _resolve_config(config)
    return _plot_timeseries_core(
        df,
        output_dir,
        "rainfall_discharge_timeseries_log_y",
        cfg,
        log_y=True,
        title_key="timeseries_log_title",
        rainfall_events=rainfall_events,
        discharge_peaks=discharge_peaks,
        show_peaks=bool(cfg["layout"]["show_peaks_on_timeseries"]),
    )


def plot_peak_events(
    df: pd.DataFrame,
    rainfall_events: pd.DataFrame,
    discharge_peaks: pd.DataFrame,
    output_dir: Path,
    config: dict[str, Any] | None = None,
) -> list[Path]:
    """Plot static time series highlighting detected rainfall and discharge peaks."""
    cfg = _resolve_config(config)
    return _plot_timeseries_core(
        df,
        output_dir,
        "peak_events",
        cfg,
        log_y=False,
        title_key="peaks_title",
        rainfall_events=rainfall_events,
        discharge_peaks=discharge_peaks,
        show_peaks=True,
    )


def plot_lag_correlation(
    lag_df: pd.DataFrame,
    output_dir: Path,
    config: dict[str, Any] | None = None,
) -> list[Path]:
    """Plot static lagged rainfall-discharge correlation curve."""
    cfg = _resolve_config(config)
    colors = cfg["colors"]
    styles = cfg["styles"]
    typo = cfg["typography"]
    layout = cfg["layout"]
    labels = layout["labels"]

    with plt.rc_context({"font.family": typo["font_family"]}):
        fig, ax = plt.subplots(figsize=tuple(layout["figsize_lag"]))
        ax.plot(
            lag_df["lag_days"],
            lag_df["correlation"],
            color=colors["lag_correlation"],
            linewidth=styles["lag_linewidth"],
            linestyle=mpl_linestyle(styles["lag_linestyle"]),
            marker=mpl_marker(styles["lag_marker"]),
            markersize=styles["lag_marker_size"],
            alpha=styles["lag_alpha"],
            label=labels["series_lag"],
        )
        ax.axhline(
            0,
            color=colors["reference_line"],
            linewidth=styles["reference_linewidth"],
            linestyle=mpl_linestyle(styles["reference_linestyle"]),
            alpha=styles["reference_alpha"],
        )
        _apply_axes_style(
            fig,
            ax,
            cfg,
            title=labels["lag_title"],
            xlabel=labels["lag_axis"],
            ylabel=labels["correlation_axis"],
        )
        if layout["show_legend"]:
            ax.legend(**mpl_legend_kwargs(cfg))
        return _save_figure(fig, output_dir, "lag_correlation", cfg)


def plot_rainfall_discharge_scatter(
    df: pd.DataFrame,
    output_dir: Path,
    config: dict[str, Any] | None = None,
) -> list[Path]:
    """Plot static same-day rainfall versus spring discharge scatter plot."""
    cfg = _resolve_config(config)
    colors = cfg["colors"]
    styles = cfg["styles"]
    typo = cfg["typography"]
    layout = cfg["layout"]
    labels = layout["labels"]

    with plt.rc_context({"font.family": typo["font_family"]}):
        fig, ax = plt.subplots(figsize=tuple(layout["figsize_scatter"]))
        ax.scatter(
            df["rainfall_mm"],
            df["spring_discharge_m3s"],
            color=colors["scatter_points"],
            marker=mpl_marker(styles["scatter_marker"]),
            s=styles["scatter_marker_size"] ** 2,
            alpha=styles["scatter_alpha"],
            edgecolors=colors["marker_edge"],
            linewidths=styles["scatter_edge_width"],
            label=labels["series_scatter"],
        )
        _apply_axes_style(
            fig,
            ax,
            cfg,
            title=labels["scatter_title"],
            xlabel=labels["rainfall_axis"],
            ylabel=labels["discharge_axis"],
        )
        if layout["show_legend"]:
            ax.legend(**mpl_legend_kwargs(cfg))
        return _save_figure(fig, output_dir, "rainfall_discharge_scatter", cfg)


def plot_discharge_histogram(
    df: pd.DataFrame,
    output_dir: Path,
    config: dict[str, Any] | None = None,
) -> list[Path]:
    """Plot static spring discharge frequency distribution."""
    cfg = _resolve_config(config)
    colors = cfg["colors"]
    styles = cfg["styles"]
    typo = cfg["typography"]
    layout = cfg["layout"]
    labels = layout["labels"]

    with plt.rc_context({"font.family": typo["font_family"]}):
        fig, ax = plt.subplots(figsize=tuple(layout["figsize_histogram"]))
        ax.hist(
            df["spring_discharge_m3s"].dropna(),
            bins=int(styles["histogram_bins"]),
            color=colors["discharge"],
            alpha=styles["histogram_alpha"],
            edgecolor=colors["marker_edge"],
            label=labels["series_discharge"],
        )
        _apply_axes_style(
            fig,
            ax,
            cfg,
            title=labels["histogram_title"],
            xlabel=labels["discharge_axis"],
            ylabel=labels["frequency_axis"],
            grid_axis="y",
        )
        if layout["show_legend"]:
            ax.legend(**mpl_legend_kwargs(cfg))
        return _save_figure(fig, output_dir, "discharge_histogram", cfg)


def create_all_figures(
    df: pd.DataFrame,
    lag_df: pd.DataFrame,
    output_dir: Path,
    config: dict[str, Any] | None = None,
    rainfall_events: pd.DataFrame | None = None,
    discharge_peaks: pd.DataFrame | None = None,
) -> list[Path]:
    """Generate all static publication-quality figures and return their file paths."""
    cfg = _resolve_config(config)
    paths: list[Path] = []
    paths.extend(plot_rainfall_discharge_timeseries(df, output_dir, cfg, rainfall_events, discharge_peaks))
    paths.extend(plot_rainfall_discharge_timeseries_log_y(df, output_dir, cfg, rainfall_events, discharge_peaks))
    paths.extend(plot_lag_correlation(lag_df, output_dir, cfg))
    paths.extend(plot_rainfall_discharge_scatter(df, output_dir, cfg))
    paths.extend(plot_discharge_histogram(df, output_dir, cfg))
    if rainfall_events is not None or discharge_peaks is not None:
        paths.extend(
            plot_peak_events(
                df,
                rainfall_events if rainfall_events is not None else df.iloc[0:0],
                discharge_peaks if discharge_peaks is not None else df.iloc[0:0],
                output_dir,
                cfg,
            )
        )
    return paths
