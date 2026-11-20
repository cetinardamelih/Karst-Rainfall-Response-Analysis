from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.downsampling import build_webgl_rainfall_stems, downsample_timeseries
from src.plot_config import (
    hex_to_rgba,
    plotly_legend_dict,
    plotly_linestyle,
    plotly_marker,
)
from src.preprocessing import normalize_series, positive_for_log


PLOT_DRAG_MODES: dict[str, str] = {
    "Zoom": "zoom",
    "Pan": "pan",
    "Select box": "select",
    "Lasso": "lasso",
    "Draw line": "drawline",
    "Free draw": "drawopenpath",
    "Draw rectangle": "drawrect",
    "Draw circle": "drawcircle",
}


def get_plotly_chart_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return Plotly interaction & modebar config driven by central config."""
    return {
        "displaylogo": False,
        "scrollZoom": True,
        "doubleClick": "reset+autosize",
        "modeBarButtonsToAdd": [
            "drawline",
            "drawopenpath",
            "drawclosedpath",
            "drawrect",
            "drawcircle",
            "eraseshape",
            "toggleSpikelines",
        ],
        "toImageButtonOptions": {
            "format": "png",
            "filename": "karst_plot",
            "scale": int(config["performance"]["export_image_scale"]),
        },
    }


def _scatter_cls(config: dict[str, Any]):
    return go.Scattergl if config["performance"]["use_webgl"] else go.Scatter


def _grid_color(config: dict[str, Any]) -> str:
    return hex_to_rgba(config["colors"]["grid"], float(config["layout"]["grid_alpha"]))


def _apply_plotly_style(
    fig: go.Figure,
    config: dict[str, Any],
    *,
    title: str,
    height: int,
    dragmode: str,
    is_timeseries: bool = False,
) -> go.Figure:
    """Apply all centralized cosmetic, typography, grid, legend, and interaction settings."""
    colors = config["colors"]
    styles = config["styles"]
    typo = config["typography"]
    layout = config["layout"]
    perf = config["performance"]

    grid_rgba = _grid_color(config)
    show_grid = bool(layout["show_grid"])

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(
                family=typo["font_family"],
                size=typo["title_size"],
                color=colors["heading"],
            ),
        ),
        font=dict(
            family=typo["font_family"],
            size=typo["tick_size"],
            color=colors["text"],
        ),
        paper_bgcolor=colors["background"],
        plot_bgcolor=colors["plot_background"],
        height=int(height),
        showlegend=bool(layout["show_legend"]),
        legend=plotly_legend_dict(config),
        dragmode=dragmode,
        hovermode="x unified" if is_timeseries else "closest",
        uirevision="karst-plots",
        newshape=dict(
            line=dict(
                color=colors["discharge_peak"],
                width=styles["annotation_linewidth"],
            ),
            opacity=styles["annotation_alpha"],
            fillcolor=colors["annotation_fill"],
        ),
        modebar=dict(orientation="h"),
        margin=dict(t=65, r=65, b=55, l=65),
    )

    axis_common = dict(
        showgrid=show_grid,
        gridcolor=grid_rgba,
        gridwidth=layout["grid_linewidth"],
        griddash=plotly_linestyle(layout["grid_linestyle"]),
        linecolor=colors["grid"],
        tickfont=dict(
            family=typo["font_family"],
            size=typo["tick_size"],
            color=colors["text"],
        ),
        title_font=dict(
            family=typo["font_family"],
            size=typo["axis_label_size"],
            color=colors["text"],
        ),
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
    )
    fig.update_xaxes(**axis_common)
    fig.update_yaxes(**axis_common)

    if is_timeseries:
        xaxis_extra: dict[str, Any] = {
            "rangeslider": dict(visible=bool(perf["show_rangeslider"])),
            "rangeselector": dict(
                bgcolor=colors["code_background"],
                font=dict(color=colors["text"], size=max(9, int(typo["tick_size"]) - 1)),
                buttons=[
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="All"),
                ],
            ),
        }
        fig.update_xaxes(**xaxis_extra, row=1, col=1) if getattr(fig, "_grid_ref", None) else fig.update_xaxes(**xaxis_extra)

    return fig


def _add_rainfall_trace(
    fig: go.Figure,
    dates: pd.Series,
    rainfall: pd.Series,
    config: dict[str, Any],
    *,
    row: int | None = None,
    col: int | None = None,
    secondary_y: bool = True,
) -> None:
    """Add rainfall as fast WebGL stems (long series), line, or bars (short series)."""
    colors = config["colors"]
    styles = config["styles"]
    labels = config["layout"]["labels"]
    perf = config["performance"]
    scatter_cls = _scatter_cls(config)

    trace_kwargs: dict[str, Any] = {"secondary_y": secondary_y}
    if row is not None and col is not None:
        trace_kwargs.update({"row": row, "col": col})

    if styles["rainfall_display"] == "line":
        trace = scatter_cls(
            x=dates,
            y=rainfall,
            mode="lines",
            name=labels["series_rainfall"],
            line=dict(
                color=colors["rainfall"],
                width=styles["rainfall_linewidth"],
                dash=plotly_linestyle(styles["rainfall_linestyle"]),
            ),
            opacity=styles["rainfall_alpha"],
        )
    elif perf["use_webgl"] and len(dates) > int(perf["rainfall_stem_threshold"]):
        stem_x, stem_y = build_webgl_rainfall_stems(dates, rainfall, baseline=0.0)
        trace = scatter_cls(
            x=stem_x,
            y=stem_y,
            mode="lines",
            name=labels["series_rainfall"],
            line=dict(
                color=colors["rainfall"],
                width=max(1.5, float(styles["rainfall_linewidth"])),
            ),
            opacity=styles["rainfall_alpha"],
            connectgaps=False,
        )
    else:
        trace = go.Bar(
            x=dates,
            y=rainfall,
            name=labels["series_rainfall"],
            marker_color=colors["rainfall"],
            opacity=styles["rainfall_alpha"],
        )

    fig.add_trace(trace, **trace_kwargs)


def plot_time_series(
    df: pd.DataFrame,
    config: dict[str, Any],
    *,
    rolling_window: int = 7,
    show_rolling: bool = True,
    normalize: bool = False,
    discharge_axis_type: str = "linear",
    rainfall_events: pd.DataFrame | None = None,
    discharge_peaks: pd.DataFrame | None = None,
    dragmode: str = "zoom",
) -> tuple[go.Figure, bool]:
    """Create WebGL-accelerated rainfall-discharge time series with peak-preserving LTTB."""
    colors = config["colors"]
    styles = config["styles"]
    layout = config["layout"]
    labels = layout["labels"]
    perf = config["performance"]
    scatter_cls = _scatter_cls(config)

    plot_df = df.copy()
    plot_df["_rain_plot"] = normalize_series(plot_df["rainfall_mm"]) if normalize else plot_df["rainfall_mm"]
    plot_df["_discharge_plot"] = (
        normalize_series(plot_df["spring_discharge_m3s"]) if normalize else plot_df["spring_discharge_m3s"]
    )
    if discharge_axis_type == "log":
        plot_df["_discharge_plot"] = positive_for_log(plot_df["_discharge_plot"])
    plot_df["_rolling_plot"] = plot_df["_discharge_plot"].rolling(rolling_window, min_periods=1).mean()

    preserve_dates: pd.Series | None = None
    if discharge_peaks is not None and not discharge_peaks.empty:
        preserve_dates = discharge_peaks["date"]

    ds_df, was_downsampled = downsample_timeseries(
        plot_df,
        date_col="date",
        value_col="_discharge_plot",
        threshold=int(perf["downsample_threshold"]),
        target_points=int(perf["downsample_target_points"]),
        preserve_dates=preserve_dates,
    )

    show_temp = (
        bool(layout["show_temperature"])
        and "mean_temperature_C" in ds_df.columns
        and ds_df["mean_temperature_C"].notna().any()
    )

    if show_temp:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.74, 0.26],
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
        )
        row_kw = {"row": 1, "col": 1}
    else:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        row_kw = {}

    # Rainfall stems/bars use full wet-day set (only wet days emitted, very lightweight in WebGL)
    _add_rainfall_trace(
        fig,
        plot_df["date"],
        plot_df["_rain_plot"],
        config,
        row=row_kw.get("row"),
        col=row_kw.get("col"),
        secondary_y=True,
    )

    fig.add_trace(
        scatter_cls(
            x=ds_df["date"],
            y=ds_df["_discharge_plot"],
            mode="lines",
            name=labels["series_discharge"],
            line=dict(
                color=colors["discharge"],
                width=styles["discharge_linewidth"],
                dash=plotly_linestyle(styles["discharge_linestyle"]),
            ),
            opacity=styles["discharge_alpha"],
        ),
        secondary_y=False,
        **row_kw,
    )

    if show_rolling:
        fig.add_trace(
            scatter_cls(
                x=ds_df["date"],
                y=ds_df["_rolling_plot"],
                mode="lines",
                name=f"{rolling_window}d {labels['series_rolling']}",
                line=dict(
                    color=colors["rolling_mean"],
                    width=styles["rolling_linewidth"],
                    dash=plotly_linestyle(styles["rolling_linestyle"]),
                ),
                opacity=styles["rolling_alpha"],
            ),
            secondary_y=False,
            **row_kw,
        )

    if layout["show_peaks_on_timeseries"]:
        if rainfall_events is not None and not rainfall_events.empty and not normalize:
            fig.add_trace(
                scatter_cls(
                    x=rainfall_events["date"],
                    y=rainfall_events["rainfall_mm"],
                    mode="markers",
                    name=labels["series_rainfall_peaks"],
                    marker=dict(
                        color=colors["rainfall_peak"],
                        size=styles["rainfall_peak_marker_size"],
                        symbol=plotly_marker(styles["rainfall_peak_marker"]),
                        opacity=styles["rainfall_peak_alpha"],
                        line=dict(color=colors["marker_edge"], width=styles["scatter_edge_width"]),
                    ),
                ),
                secondary_y=True,
                **row_kw,
            )
        if discharge_peaks is not None and not discharge_peaks.empty and not normalize:
            peak_y = (
                positive_for_log(discharge_peaks["spring_discharge_m3s"])
                if discharge_axis_type == "log"
                else discharge_peaks["spring_discharge_m3s"]
            )
            fig.add_trace(
                scatter_cls(
                    x=discharge_peaks["date"],
                    y=peak_y,
                    mode="markers",
                    name=labels["series_discharge_peaks"],
                    marker=dict(
                        color=colors["discharge_peak"],
                        size=styles["discharge_peak_marker_size"],
                        symbol=plotly_marker(styles["discharge_peak_marker"]),
                        opacity=styles["discharge_peak_alpha"],
                        line=dict(color=colors["marker_edge"], width=styles["scatter_edge_width"]),
                    ),
                ),
                secondary_y=False,
                **row_kw,
            )

    if show_temp:
        fig.add_trace(
            scatter_cls(
                x=ds_df["date"],
                y=ds_df["mean_temperature_C"],
                mode="lines",
                name=labels["series_temperature"],
                line=dict(
                    color=colors["temperature"],
                    width=styles["temperature_linewidth"],
                    dash=plotly_linestyle(styles["temperature_linestyle"]),
                ),
                opacity=styles["temperature_alpha"],
            ),
            row=2,
            col=1,
        )

    if normalize:
        discharge_title = labels["discharge_normalized_axis"]
        rain_title = labels["rainfall_normalized_axis"]
    else:
        discharge_title = labels["discharge_log_axis"] if discharge_axis_type == "log" else labels["discharge_axis"]
        rain_title = labels["rainfall_axis"]

    title = labels["timeseries_log_title"] if discharge_axis_type == "log" else labels["timeseries_title"]
    height = int(layout["interactive_height"]) + (140 if show_temp else 0)
    _apply_plotly_style(fig, config, title=title, height=height, dragmode=dragmode, is_timeseries=True)

    fig.update_yaxes(title_text=discharge_title, type=discharge_axis_type, secondary_y=False, **row_kw)
    fig.update_yaxes(title_text=rain_title, autorange="reversed", showgrid=False, secondary_y=True, **row_kw)
    if show_temp:
        fig.update_yaxes(title_text=labels["temperature_axis"], row=2, col=1)
        fig.update_xaxes(title_text=labels["date_axis"], row=2, col=1)
    else:
        fig.update_xaxes(title_text=labels["date_axis"])

    return fig, was_downsampled


def plot_lag(lag_df: pd.DataFrame, config: dict[str, Any], dragmode: str = "zoom") -> go.Figure:
    """Create interactive lag correlation plot driven by central config."""
    colors = config["colors"]
    styles = config["styles"]
    layout = config["layout"]
    labels = layout["labels"]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=lag_df["lag_days"],
            y=lag_df["correlation"],
            mode="lines+markers",
            name=labels["series_lag"],
            line=dict(
                color=colors["lag_correlation"],
                width=styles["lag_linewidth"],
                dash=plotly_linestyle(styles["lag_linestyle"]),
            ),
            marker=dict(
                color=colors["lag_correlation"],
                size=styles["lag_marker_size"],
                symbol=plotly_marker(styles["lag_marker"]),
            ),
            opacity=styles["lag_alpha"],
        )
    )
    fig.add_hline(
        y=0,
        line_width=styles["reference_linewidth"],
        line_dash=plotly_linestyle(styles["reference_linestyle"]),
        line_color=colors["reference_line"],
        opacity=styles["reference_alpha"],
    )
    _apply_plotly_style(
        fig,
        config,
        title=labels["lag_title"],
        height=int(layout["interactive_compact_height"]),
        dragmode=dragmode,
    )
    fig.update_xaxes(title_text=labels["lag_axis"])
    fig.update_yaxes(title_text=labels["correlation_axis"])
    return fig


def plot_scatter(
    df: pd.DataFrame,
    config: dict[str, Any],
    *,
    normalize: bool = False,
    dragmode: str = "zoom",
) -> go.Figure:
    """Create WebGL rainfall-discharge scatter plot."""
    colors = config["colors"]
    styles = config["styles"]
    layout = config["layout"]
    labels = layout["labels"]
    scatter_cls = _scatter_cls(config)

    x = normalize_series(df["rainfall_mm"]) if normalize else df["rainfall_mm"]
    y = normalize_series(df["spring_discharge_m3s"]) if normalize else df["spring_discharge_m3s"]

    fig = go.Figure()
    fig.add_trace(
        scatter_cls(
            x=x,
            y=y,
            mode="markers",
            name=labels["series_scatter"],
            text=df["date"].dt.strftime("%Y-%m-%d"),
            marker=dict(
                color=colors["scatter_points"],
                size=styles["scatter_marker_size"],
                symbol=plotly_marker(styles["scatter_marker"]),
                opacity=styles["scatter_alpha"],
                line=dict(color=colors["marker_edge"], width=styles["scatter_edge_width"]),
            ),
        )
    )
    _apply_plotly_style(
        fig,
        config,
        title=labels["scatter_title"],
        height=int(layout["interactive_compact_height"]),
        dragmode=dragmode,
    )
    fig.update_xaxes(title_text=labels["rainfall_normalized_axis"] if normalize else labels["rainfall_axis"])
    fig.update_yaxes(title_text=labels["discharge_normalized_axis"] if normalize else labels["discharge_axis"])
    return fig


def plot_distribution(df: pd.DataFrame, config: dict[str, Any], dragmode: str = "zoom") -> go.Figure:
    """Create interactive discharge histogram."""
    colors = config["colors"]
    styles = config["styles"]
    layout = config["layout"]
    labels = layout["labels"]

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=df["spring_discharge_m3s"],
            nbinsx=int(styles["histogram_bins"]),
            marker=dict(
                color=colors["discharge"],
                line=dict(color=colors["marker_edge"], width=styles["scatter_edge_width"]),
            ),
            opacity=styles["histogram_alpha"],
            name=labels["series_discharge"],
        )
    )
    _apply_plotly_style(
        fig,
        config,
        title=labels["histogram_title"],
        height=int(layout["interactive_compact_height"]),
        dragmode=dragmode,
    )
    fig.update_xaxes(title_text=labels["discharge_axis"])
    fig.update_yaxes(title_text=labels["frequency_axis"])
    return fig


def plot_rolling(
    df: pd.DataFrame,
    config: dict[str, Any],
    *,
    rolling_window: int = 7,
    dragmode: str = "zoom",
) -> tuple[go.Figure, bool]:
    """Create WebGL rolling mean spring discharge chart with LTTB downsampling."""
    colors = config["colors"]
    styles = config["styles"]
    layout = config["layout"]
    labels = layout["labels"]
    perf = config["performance"]
    scatter_cls = _scatter_cls(config)

    plot_df = df[["date", "spring_discharge_m3s"]].copy()
    plot_df["_rolling"] = plot_df["spring_discharge_m3s"].rolling(rolling_window, min_periods=1).mean()
    ds_df, was_downsampled = downsample_timeseries(
        plot_df,
        date_col="date",
        value_col="spring_discharge_m3s",
        threshold=int(perf["downsample_threshold"]),
        target_points=int(perf["downsample_target_points"]),
    )

    fig = go.Figure()
    fig.add_trace(
        scatter_cls(
            x=ds_df["date"],
            y=ds_df["spring_discharge_m3s"],
            mode="lines",
            name=labels["series_raw_discharge"],
            line=dict(
                color=colors["raw_discharge"],
                width=styles["raw_discharge_linewidth"],
                dash=plotly_linestyle(styles["raw_discharge_linestyle"]),
            ),
            opacity=styles["raw_discharge_alpha"],
        )
    )
    fig.add_trace(
        scatter_cls(
            x=ds_df["date"],
            y=ds_df["_rolling"],
            mode="lines",
            name=f"{rolling_window}d {labels['series_rolling']}",
            line=dict(
                color=colors["rolling_mean"],
                width=styles["rolling_linewidth"],
                dash=plotly_linestyle(styles["rolling_linestyle"]),
            ),
            opacity=styles["rolling_alpha"],
        )
    )
    _apply_plotly_style(
        fig,
        config,
        title=labels["rolling_title"],
        height=int(layout["interactive_compact_height"]),
        dragmode=dragmode,
        is_timeseries=True,
    )
    fig.update_xaxes(title_text=labels["date_axis"])
    fig.update_yaxes(title_text=labels["discharge_axis"])
    return fig, was_downsampled


def plot_peaks(
    df: pd.DataFrame,
    rainfall_events: pd.DataFrame,
    discharge_peaks: pd.DataFrame,
    config: dict[str, Any],
    *,
    dragmode: str = "zoom",
) -> tuple[go.Figure, bool]:
    """Create WebGL peak rainfall and discharge event figure."""
    colors = config["colors"]
    styles = config["styles"]
    layout = config["layout"]
    labels = layout["labels"]
    perf = config["performance"]
    scatter_cls = _scatter_cls(config)

    preserve_dates = discharge_peaks["date"] if not discharge_peaks.empty else None
    ds_df, was_downsampled = downsample_timeseries(
        df,
        date_col="date",
        value_col="spring_discharge_m3s",
        threshold=int(perf["downsample_threshold"]),
        target_points=int(perf["downsample_target_points"]),
        preserve_dates=preserve_dates,
    )

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    _add_rainfall_trace(fig, df["date"], df["rainfall_mm"], config, secondary_y=True)

    fig.add_trace(
        scatter_cls(
            x=ds_df["date"],
            y=ds_df["spring_discharge_m3s"],
            mode="lines",
            name=labels["series_discharge"],
            line=dict(
                color=colors["discharge"],
                width=styles["discharge_linewidth"],
                dash=plotly_linestyle(styles["discharge_linestyle"]),
            ),
            opacity=styles["discharge_alpha"],
        ),
        secondary_y=False,
    )

    if not rainfall_events.empty:
        fig.add_trace(
            scatter_cls(
                x=rainfall_events["date"],
                y=rainfall_events["rainfall_mm"],
                mode="markers",
                name=labels["series_rainfall_peaks"],
                marker=dict(
                    color=colors["rainfall_peak"],
                    size=styles["rainfall_peak_marker_size"],
                    symbol=plotly_marker(styles["rainfall_peak_marker"]),
                    opacity=styles["rainfall_peak_alpha"],
                    line=dict(color=colors["marker_edge"], width=styles["scatter_edge_width"]),
                ),
            ),
            secondary_y=True,
        )

    if not discharge_peaks.empty:
        fig.add_trace(
            scatter_cls(
                x=discharge_peaks["date"],
                y=discharge_peaks["spring_discharge_m3s"],
                mode="markers",
                name=labels["series_discharge_peaks"],
                marker=dict(
                    color=colors["discharge_peak"],
                    size=styles["discharge_peak_marker_size"],
                    symbol=plotly_marker(styles["discharge_peak_marker"]),
                    opacity=styles["discharge_peak_alpha"],
                    line=dict(color=colors["marker_edge"], width=styles["scatter_edge_width"]),
                ),
            ),
            secondary_y=False,
        )

    _apply_plotly_style(
        fig,
        config,
        title=labels["peaks_title"],
        height=int(layout["interactive_height"]),
        dragmode=dragmode,
        is_timeseries=True,
    )
    fig.update_xaxes(title_text=labels["date_axis"])
    fig.update_yaxes(title_text=labels["discharge_axis"], secondary_y=False)
    fig.update_yaxes(title_text=labels["rainfall_axis"], autorange="reversed", showgrid=False, secondary_y=True)
    return fig, was_downsampled
