from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import (
    basic_statistics,
    find_discharge_peaks,
    find_rainfall_events,
    lag_correlations,
    rainfall_discharge_correlation,
    estimate_lag_time,
)
from src.preprocessing import clean_timeseries
from src.synthetic_data import generate_synthetic_karst_data
from src.ui_config import CHART_COLORS, UI_TEXT


STANDARD_COLUMNS = {
    "date": "date",
    "rainfall": "rainfall_mm",
    "temperature": "mean_temperature_C",
    "discharge": "spring_discharge_m3s",
}


st.set_page_config(
    page_title=UI_TEXT["app_title"],
    layout="wide",
)

PLOTLY_DRAW_CONFIG = {
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
        "scale": 2,
    },
}

PLOT_DRAG_MODES = {
    "Zoom": "zoom",
    "Pan": "pan",
    "Select box": "select",
    "Lasso": "lasso",
    "Draw line": "drawline",
    "Free draw": "drawopenpath",
    "Draw rectangle": "drawrect",
    "Draw circle": "drawcircle",
}


def initialize_state() -> None:
    """Initialize Streamlit session state used by the app."""
    defaults: dict[str, Any] = {
        "raw_df": None,
        "mapped_df": None,
        "clean_df": None,
        "analysis": None,
        "data_source": "sample",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def sample_dataframe() -> pd.DataFrame:
    """Return the built-in synthetic sample dataset."""
    return generate_synthetic_karst_data(periods=365, seed=42)


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """Serialize a DataFrame to UTF-8 CSV bytes."""
    return df.to_csv(index=False).encode("utf-8")


def infer_column(columns: list[str], candidates: list[str]) -> str | None:
    """Infer a likely column name from lower-case candidate fragments."""
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        for lower_name, original in lowered.items():
            if candidate in lower_name:
                return original
    return None


def normalize_input_columns(
    raw_df: pd.DataFrame,
    date_col: str,
    rainfall_col: str,
    discharge_col: str,
    temperature_col: str | None,
) -> pd.DataFrame:
    """Map user-selected columns to the internal schema used by src functions."""
    mapped = pd.DataFrame(
        {
            STANDARD_COLUMNS["date"]: pd.to_datetime(raw_df[date_col], errors="coerce"),
            STANDARD_COLUMNS["rainfall"]: pd.to_numeric(raw_df[rainfall_col], errors="coerce"),
            STANDARD_COLUMNS["discharge"]: pd.to_numeric(raw_df[discharge_col], errors="coerce"),
        }
    )

    if temperature_col and temperature_col != "None":
        mapped[STANDARD_COLUMNS["temperature"]] = pd.to_numeric(raw_df[temperature_col], errors="coerce")
    else:
        mapped[STANDARD_COLUMNS["temperature"]] = np.nan

    return mapped


def clean_with_method(df: pd.DataFrame, method: str) -> pd.DataFrame:
    """Apply user-selected missing data handling before standard cleaning."""
    cleaned = df.copy()
    if method == "Drop missing rows":
        cleaned = cleaned.dropna(subset=list(STANDARD_COLUMNS.values()))
    elif method == "Forward fill":
        cleaned = cleaned.sort_values("date").ffill()
    elif method == "Linear interpolation":
        cleaned = cleaned.sort_values("date")
        numeric_cols = ["rainfall_mm", "mean_temperature_C", "spring_discharge_m3s"]
        cleaned[numeric_cols] = cleaned[numeric_cols].interpolate(limit_direction="both")

    return clean_timeseries(cleaned)


def filter_date_range(df: pd.DataFrame, start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Filter data to the selected inclusive date range."""
    mask = (df["date"] >= pd.to_datetime(start_date)) & (df["date"] <= pd.to_datetime(end_date))
    return df.loc[mask].reset_index(drop=True)


def normalized_series(series: pd.Series) -> pd.Series:
    """Return min-max normalized values, with zero fallback for constant series."""
    min_value = series.min()
    max_value = series.max()
    if pd.isna(min_value) or pd.isna(max_value) or max_value == min_value:
        return pd.Series(np.zeros(len(series)), index=series.index)
    return (series - min_value) / (max_value - min_value)


def run_analysis(
    df: pd.DataFrame,
    max_lag_days: int,
    rainfall_percentile: float,
    discharge_prominence: float | None,
    peak_distance_days: int,
) -> dict[str, Any]:
    """Run project analysis functions and package results for the UI."""
    lag_df = lag_correlations(df, max_lag_days=max_lag_days)
    estimated_lag_days, estimated_lag_corr = estimate_lag_time(lag_df)
    rainfall_events = find_rainfall_events(df, percentile=rainfall_percentile)
    discharge_peaks = find_discharge_peaks(
        df,
        prominence=discharge_prominence,
        distance_days=peak_distance_days,
    )
    metrics = {
        "total_rainfall_mm": float(df["rainfall_mm"].sum()),
        "mean_discharge_m3s": float(df["spring_discharge_m3s"].mean()),
        "max_discharge_m3s": float(df["spring_discharge_m3s"].max()),
        "min_discharge_m3s": float(df["spring_discharge_m3s"].min()),
        "same_day_correlation": rainfall_discharge_correlation(df),
        "estimated_lag_days": estimated_lag_days,
        "estimated_lag_correlation": estimated_lag_corr,
        "rainfall_peak_count": int(len(rainfall_events)),
        "discharge_peak_count": int(len(discharge_peaks)),
    }
    return {
        "metrics": metrics,
        "lag_df": lag_df,
        "rainfall_events": rainfall_events,
        "discharge_peaks": discharge_peaks,
        "statistics": basic_statistics(df),
    }


def hydrogeology_interpretation(metrics: dict[str, Any]) -> str:
    """Create cautious hydrogeological interpretation text."""
    lag = metrics["estimated_lag_days"]
    corr = metrics["estimated_lag_correlation"]
    same_day_corr = metrics["same_day_correlation"]

    lag_text = (
        "The estimated lag time is short. Under suitable field conditions, this may be consistent "
        "with a fast-responding karst system where conduit influence is relatively pronounced."
        if lag <= 2
        else "The estimated lag time is longer. This may indicate a stronger diffuse-flow component, "
        "storage effects, or delayed recharge processes."
    )

    corr_text = (
        "The lag correlation is relatively clear, suggesting that a rainfall-discharge relationship "
        "is detectable in this dataset. Causality still requires field evidence and additional "
        "hydrological checks."
        if corr >= 0.55
        else "The lag correlation is low to moderate. Non-rainfall controls, data resolution, "
        "measurement uncertainty, or complex storage-drainage processes may be influential."
    )

    same_day_text = (
        f"The same-day correlation is {same_day_corr:.2f}. Because delayed responses are common "
        "in karst systems, this value should be interpreted together with the lag correlation."
    )

    return "\n\n".join([lag_text, corr_text, same_day_text])


def build_markdown_report(
    df: pd.DataFrame,
    analysis: dict[str, Any],
    params: dict[str, Any],
    interpretation: str,
) -> str:
    """Build a downloadable Markdown report."""
    metrics = analysis["metrics"]
    start_date = df["date"].min().date()
    end_date = df["date"].max().date()
    metric_lines = "\n".join(
        [
            f"- Total rainfall: {metrics['total_rainfall_mm']:.2f} mm",
            f"- Mean discharge: {metrics['mean_discharge_m3s']:.3f} m3/s",
            f"- Maximum discharge: {metrics['max_discharge_m3s']:.3f} m3/s",
            f"- Minimum discharge: {metrics['min_discharge_m3s']:.3f} m3/s",
            f"- Estimated lag time: {metrics['estimated_lag_days']} days",
            f"- Highest lag correlation: {metrics['estimated_lag_correlation']:.3f}",
            f"- Same-day correlation: {metrics['same_day_correlation']:.3f}",
            f"- Rainfall peak count: {metrics['rainfall_peak_count']}",
            f"- Discharge peak count: {metrics['discharge_peak_count']}",
        ]
    )
    param_lines = "\n".join([f"- {key}: {value}" for key, value in params.items()])

    return f"""# Karst Rainfall-Response Analysis Report

## Dataset Summary

- Records: {len(df)}
- Date range: {start_date} to {end_date}
- Required variables: rainfall, spring discharge, optional temperature

## Analysis Parameters

{param_lines}

## Key Metrics

{metric_lines}

## Hydrogeological Interpretation

{interpretation}

## Limitations

This MVP is intended for hydrogeological decision support, exploratory analysis, and visualization. It does not produce a standalone definitive hydrogeological model result. Field geology, recharge area definition, data quality, evapotranspiration, snowmelt, abstraction, and monitoring uncertainty should be evaluated separately.
"""


def markdown_to_html(markdown_text: str) -> str:
    """Create a simple standalone HTML report from Markdown text."""
    escaped = (
        markdown_text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    body = escaped.replace("\n", "<br>\n")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Karst Rainfall-Response Analysis Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; max-width: 920px; margin: 40px auto; line-height: 1.55; color: {CHART_COLORS["html_text"]}; }}
    h1, h2 {{ color: {CHART_COLORS["html_heading"]}; }}
    code {{ background: {CHART_COLORS["code_background"]}; padding: 2px 4px; }}
  </style>
</head>
<body>{body}</body>
</html>
"""


def enhance_plot_controls(fig: go.Figure, dragmode: str) -> go.Figure:
    """Apply shared interaction affordances to Plotly charts."""
    fig.update_layout(
        dragmode=dragmode,
        hovermode="x unified",
        uirevision="karst-plots",
        newshape=dict(
            line=dict(color=CHART_COLORS["discharge_peak"], width=3),
            opacity=0.85,
            fillcolor="rgba(204, 0, 0, 0.12)",
        ),
        modebar=dict(orientation="h"),
    )
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        rangeslider=dict(visible=True),
    )
    fig.update_yaxes(showspikes=True, spikemode="across", spikesnap="cursor")
    return fig


def show_plotly_figure(fig: go.Figure, key: str, dragmode: str) -> None:
    """Render a Plotly figure with drawing tools enabled."""
    st.plotly_chart(
        enhance_plot_controls(fig, dragmode),
        width="stretch",
        config=PLOTLY_DRAW_CONFIG,
        key=key,
    )


def positive_for_log(series: pd.Series) -> pd.Series:
    """Mask non-positive values so log-axis charts remain valid."""
    return series.where(series > 0)


def plot_time_series(
    df: pd.DataFrame,
    rolling_window: int,
    show_rolling: bool,
    normalize: bool,
    discharge_axis_type: str = "linear",
) -> go.Figure:
    """Create interactive rainfall-discharge time series figure."""
    plot_df = df.copy()
    rain = normalized_series(plot_df["rainfall_mm"]) if normalize else plot_df["rainfall_mm"]
    discharge = normalized_series(plot_df["spring_discharge_m3s"]) if normalize else plot_df["spring_discharge_m3s"]
    if discharge_axis_type == "log":
        discharge = positive_for_log(discharge)
    rolling = discharge.rolling(rolling_window, min_periods=1).mean()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=plot_df["date"], y=rain, name="Rainfall", marker_color=CHART_COLORS["rainfall"], opacity=0.45, secondary_y=True)
    fig.add_trace(go.Scatter(x=plot_df["date"], y=discharge, mode="lines", name="Discharge", line=dict(color=CHART_COLORS["discharge"], width=2)), secondary_y=False)
    if show_rolling:
        fig.add_trace(go.Scatter(x=plot_df["date"], y=rolling, mode="lines", name=f"{rolling_window}-day rolling discharge", line=dict(color=CHART_COLORS["rolling_mean"], width=2, dash="dot")), secondary_y=False)

    discharge_title = "Discharge" if normalize else "Discharge (m3/s)"
    if discharge_axis_type == "log":
        discharge_title = f"{discharge_title}, log scale"
    fig.update_yaxes(title_text=discharge_title, type=discharge_axis_type, secondary_y=False)
    fig.update_yaxes(title_text="Rainfall" if normalize else "Rainfall (mm/day)", autorange="reversed", secondary_y=True)
    title = "Rainfall and Spring Discharge Time Series"
    if discharge_axis_type == "log":
        title = "Rainfall and Spring Discharge Time Series (Log Discharge Axis)"
    fig.update_layout(title=title, height=560, hovermode="x unified", template="plotly_white")
    return fig


def plot_lag(lag_df: pd.DataFrame) -> go.Figure:
    """Create interactive lag correlation figure."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=lag_df["lag_days"], y=lag_df["correlation"], mode="lines+markers", name="Lag correlation", line=dict(color=CHART_COLORS["lag_correlation"], width=2)))
    fig.add_hline(y=0, line_width=1, line_color=CHART_COLORS["reference_line"])
    fig.update_layout(title="Lagged Rainfall-Discharge Correlation", xaxis_title="Rainfall lag (days)", yaxis_title="Pearson correlation", height=500, template="plotly_white")
    return fig


def plot_scatter(df: pd.DataFrame, normalize: bool) -> go.Figure:
    """Create rainfall-discharge scatter figure."""
    x = normalized_series(df["rainfall_mm"]) if normalize else df["rainfall_mm"]
    y = normalized_series(df["spring_discharge_m3s"]) if normalize else df["spring_discharge_m3s"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="markers", marker=dict(color=CHART_COLORS["scatter_points"], size=8, opacity=0.65), text=df["date"].dt.strftime("%Y-%m-%d"), name="Daily observations"))
    fig.update_layout(title="Rainfall vs Discharge", xaxis_title="Rainfall" if normalize else "Rainfall (mm/day)", yaxis_title="Discharge" if normalize else "Discharge (m3/s)", height=500, template="plotly_white")
    return fig


def plot_distribution(df: pd.DataFrame) -> go.Figure:
    """Create discharge histogram figure."""
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=df["spring_discharge_m3s"], nbinsx=30, marker_color=CHART_COLORS["discharge"], name="Discharge"))
    fig.update_layout(title="Spring Discharge Distribution", xaxis_title="Discharge (m3/s)", yaxis_title="Frequency", height=500, template="plotly_white")
    return fig


def plot_rolling(df: pd.DataFrame, rolling_window: int) -> go.Figure:
    """Create rolling mean discharge figure."""
    rolling = df["spring_discharge_m3s"].rolling(rolling_window, min_periods=1).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["spring_discharge_m3s"], mode="lines", name="Daily discharge", line=dict(color=CHART_COLORS["raw_discharge"], width=1)))
    fig.add_trace(go.Scatter(x=df["date"], y=rolling, mode="lines", name=f"{rolling_window}-day rolling mean", line=dict(color=CHART_COLORS["rolling_mean"], width=3)))
    fig.update_layout(title="Rolling Mean Spring Discharge", xaxis_title="Date", yaxis_title="Discharge (m3/s)", height=500, hovermode="x unified", template="plotly_white")
    return fig


def plot_peaks(df: pd.DataFrame, rainfall_events: pd.DataFrame, discharge_peaks: pd.DataFrame) -> go.Figure:
    """Create peak event figure with rainfall and discharge markers."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=df["date"], y=df["rainfall_mm"], name="Rainfall", marker_color=CHART_COLORS["rainfall"], opacity=0.35, secondary_y=True)
    fig.add_trace(go.Scatter(x=df["date"], y=df["spring_discharge_m3s"], mode="lines", name="Discharge", line=dict(color=CHART_COLORS["discharge"], width=2)), secondary_y=False)
    if not rainfall_events.empty:
        fig.add_trace(go.Scatter(x=rainfall_events["date"], y=rainfall_events["rainfall_mm"], mode="markers", name="Rainfall peaks", marker=dict(color=CHART_COLORS["rainfall_peak"], size=11, symbol="triangle-down")), secondary_y=True)
    if not discharge_peaks.empty:
        fig.add_trace(go.Scatter(x=discharge_peaks["date"], y=discharge_peaks["spring_discharge_m3s"], mode="markers", name="Discharge peaks", marker=dict(color=CHART_COLORS["discharge_peak"], size=11, symbol="circle")), secondary_y=False)
    fig.update_yaxes(title_text="Discharge (m3/s)", secondary_y=False)
    fig.update_yaxes(title_text="Rainfall (mm/day)", autorange="reversed", secondary_y=True)
    fig.update_layout(title="Peak Rainfall and Discharge Events", height=560, hovermode="x unified", template="plotly_white")
    return fig


def figure_download_controls(fig: go.Figure, stem: str) -> None:
    """Show HTML and optional PNG download controls for a Plotly figure."""
    html = fig.to_html(full_html=True, include_plotlyjs="cdn")
    col_html, col_png = st.columns(2)
    col_html.download_button(
        "Download interactive HTML",
        data=html.encode("utf-8"),
        file_name=f"{stem}.html",
        mime="text/html",
        width="stretch",
    )
    try:
        png_bytes = fig.to_image(format="png", scale=2)
        col_png.download_button(
            "Download PNG",
            data=png_bytes,
            file_name=f"{stem}.png",
            mime="image/png",
            width="stretch",
        )
    except Exception:
        col_png.caption("PNG export requires the optional kaleido package.")


def show_home() -> None:
    """Render app intro."""
    st.title(UI_TEXT["app_title"])
    st.write(UI_TEXT["app_intro"])
    st.info(UI_TEXT["decision_support_note"])
    flow_cols = st.columns(5)
    for col, label in zip(
        flow_cols,
        UI_TEXT["workflow_steps"],
    ):
        col.markdown(f"**{label}**")


def sidebar_controls(raw_df: pd.DataFrame) -> dict[str, Any]:
    """Render sidebar column mapping and analysis controls."""
    st.sidebar.header(UI_TEXT["column_mapping"])
    columns = raw_df.columns.tolist()

    inferred_date = infer_column(columns, ["date", "time"])
    inferred_rain = infer_column(columns, ["rainfall", "precip", "rain"])
    inferred_discharge = infer_column(columns, ["discharge", "flow", "spring"])
    inferred_temp = infer_column(columns, ["temperature", "temp"])

    date_col = st.sidebar.selectbox(UI_TEXT["date_column"], columns, index=columns.index(inferred_date) if inferred_date in columns else 0)
    rainfall_col = st.sidebar.selectbox(UI_TEXT["rainfall_column"], columns, index=columns.index(inferred_rain) if inferred_rain in columns else 0)
    discharge_col = st.sidebar.selectbox(UI_TEXT["discharge_column"], columns, index=columns.index(inferred_discharge) if inferred_discharge in columns else 0)
    temperature_options = ["None"] + columns
    temperature_col = st.sidebar.selectbox(
        UI_TEXT["temperature_column"],
        temperature_options,
        index=temperature_options.index(inferred_temp) if inferred_temp in temperature_options else 0,
    )

    st.sidebar.header(UI_TEXT["preprocessing"])
    cleaning_method = st.sidebar.radio(
        UI_TEXT["missing_value_handling"],
        ["Linear interpolation", "Drop missing rows", "Forward fill"],
        index=0,
    )

    st.sidebar.header(UI_TEXT["analysis_settings"])
    max_lag_days = st.sidebar.slider(UI_TEXT["max_lag_days"], min_value=3, max_value=60, value=14)
    rainfall_percentile = st.sidebar.slider(UI_TEXT["rainfall_peak_percentile"], min_value=70.0, max_value=99.0, value=90.0, step=1.0)
    use_auto_prominence = st.sidebar.checkbox(UI_TEXT["auto_discharge_peak_prominence"], value=True)
    discharge_prominence = None
    if not use_auto_prominence:
        discharge_prominence = st.sidebar.number_input(UI_TEXT["minimum_discharge_peak_prominence"], min_value=0.0, value=0.5, step=0.1)
    peak_distance_days = st.sidebar.slider(UI_TEXT["minimum_distance_between_peaks"], min_value=1, max_value=30, value=3)
    rolling_window = st.sidebar.slider(UI_TEXT["rolling_average_window"], min_value=1, max_value=30, value=7)
    show_rolling = st.sidebar.checkbox(UI_TEXT["show_rolling_average"], value=True)
    normalize = st.sidebar.checkbox(UI_TEXT["normalize_charts"], value=False)
    plot_mode_label = st.sidebar.selectbox(
        UI_TEXT["plot_interaction_mode"],
        list(PLOT_DRAG_MODES.keys()),
        index=0,
    )

    return {
        "date_col": date_col,
        "rainfall_col": rainfall_col,
        "discharge_col": discharge_col,
        "temperature_col": temperature_col,
        "cleaning_method": cleaning_method,
        "max_lag_days": max_lag_days,
        "rainfall_percentile": rainfall_percentile,
        "discharge_prominence": discharge_prominence,
        "peak_distance_days": peak_distance_days,
        "rolling_window": rolling_window,
        "show_rolling": show_rolling,
        "normalize": normalize,
        "plot_dragmode": PLOT_DRAG_MODES[plot_mode_label],
    }


initialize_state()
show_home()

st.sidebar.header(UI_TEXT["data_source"])
uploaded_file = st.sidebar.file_uploader(UI_TEXT["upload_csv"], type=["csv"])
use_sample = st.sidebar.button(UI_TEXT["load_sample_dataset"], width="stretch")

sample_df = sample_dataframe()
download_sample_df = sample_df.rename(
    columns={
        "mean_temperature_C": "temperature_C",
        "spring_discharge_m3s": "discharge_m3s",
    }
)
st.sidebar.download_button(
    UI_TEXT["download_sample_csv"],
    data=dataframe_to_csv_bytes(download_sample_df),
    file_name="synthetic_karst_timeseries.csv",
    mime="text/csv",
    width="stretch",
)

with st.expander(UI_TEXT["example_csv_format"], expanded=False):
    st.dataframe(download_sample_df.head(5), width="stretch")

if uploaded_file is not None:
    try:
        st.session_state.raw_df = pd.read_csv(uploaded_file)
        st.session_state.data_source = "uploaded"
    except Exception as exc:
        st.error(f"CSV could not be read. Please check the file format. Details: {exc}")
elif use_sample or st.session_state.raw_df is None:
    st.session_state.raw_df = sample_df
    st.session_state.data_source = "sample"

raw_df = st.session_state.raw_df

if raw_df is None or raw_df.empty:
    st.warning(UI_TEXT["load_data_to_begin"])
    st.stop()

controls = sidebar_controls(raw_df)

st.subheader(UI_TEXT["data_preview"])
source_label = UI_TEXT["uploaded_csv"] if st.session_state.data_source == "uploaded" else UI_TEXT["sample_dataset"]
st.caption(f"{UI_TEXT['current_source']}: {source_label}")
st.dataframe(raw_df.head(10), width="stretch")

missing_report = raw_df.isna().sum().rename("missing_count").reset_index().rename(columns={"index": "column"})
col_missing, col_shape, col_parse = st.columns(3)
col_shape.metric(UI_TEXT["rows"], f"{len(raw_df):,}")
col_shape.metric(UI_TEXT["columns"], f"{len(raw_df.columns):,}")
col_missing.metric(UI_TEXT["missing_cells"], f"{int(raw_df.isna().sum().sum()):,}")

date_preview = pd.to_datetime(raw_df[controls["date_col"]], errors="coerce")
parse_rate = date_preview.notna().mean() * 100
col_parse.metric(UI_TEXT["date_parse_success"], f"{parse_rate:.1f}%")

with st.expander(UI_TEXT["missing_value_report"], expanded=False):
    st.dataframe(missing_report, width="stretch")

try:
    mapped_df = normalize_input_columns(
        raw_df,
        controls["date_col"],
        controls["rainfall_col"],
        controls["discharge_col"],
        controls["temperature_col"],
    )
except Exception as exc:
    st.error(f"Column mapping failed: {exc}")
    st.stop()

trace_rain = int((mapped_df["rainfall_mm"] < 1.0).sum())
negative_discharge = int((mapped_df["spring_discharge_m3s"] < 0).sum())
if trace_rain:
    st.warning(f"{trace_rain} rainfall value(s) below 1.0 mm detected. Cleaning sets them to zero.")
if negative_discharge:
    st.warning(f"{negative_discharge} negative discharge value(s) detected. Cleaning clips discharge at zero.")
if not mapped_df["date"].is_monotonic_increasing:
    st.info("Dates are not sorted in the input. The analysis will sort them chronologically.")

clean_df = clean_with_method(mapped_df, controls["cleaning_method"])
if clean_df.empty:
    st.error("No valid rows remain after preprocessing. Please check column mapping and missing values.")
    st.stop()

date_min = clean_df["date"].min().date()
date_max = clean_df["date"].max().date()
selected_range = st.sidebar.date_input(UI_TEXT["date_range"], value=(date_min, date_max), min_value=date_min, max_value=date_max)
if isinstance(selected_range, tuple) and len(selected_range) == 2:
    clean_df = filter_date_range(clean_df, pd.Timestamp(selected_range[0]), pd.Timestamp(selected_range[1]))

if len(clean_df) < controls["max_lag_days"] + 5:
    st.warning("The selected date range is short relative to the maximum lag. Consider reducing max lag days.")

st.subheader(UI_TEXT["preprocessing_check"])
check_cols = st.columns(4)
check_cols[0].metric(UI_TEXT["clean_rows"], f"{len(clean_df):,}")
check_cols[1].metric(UI_TEXT["start_date"], str(clean_df["date"].min().date()))
check_cols[2].metric(UI_TEXT["end_date"], str(clean_df["date"].max().date()))
check_cols[3].metric(UI_TEXT["remaining_missing"], f"{int(clean_df.isna().sum().sum()):,}")

run_clicked = st.button(UI_TEXT["run_analysis"], type="primary", width="stretch")
if run_clicked:
    try:
        st.session_state.clean_df = clean_df
        st.session_state.analysis = run_analysis(
            clean_df,
            max_lag_days=controls["max_lag_days"],
            rainfall_percentile=controls["rainfall_percentile"],
            discharge_prominence=controls["discharge_prominence"],
            peak_distance_days=controls["peak_distance_days"],
        )
        st.session_state.params = {
            "max_lag_days": controls["max_lag_days"],
            "rainfall_peak_percentile": controls["rainfall_percentile"],
            "discharge_peak_prominence": "auto" if controls["discharge_prominence"] is None else controls["discharge_prominence"],
            "peak_distance_days": controls["peak_distance_days"],
            "rolling_average_window_days": controls["rolling_window"],
            "cleaning_method": controls["cleaning_method"],
            "date_range": f"{clean_df['date'].min().date()} to {clean_df['date'].max().date()}",
        }
        st.success(UI_TEXT["analysis_completed"])
    except Exception as exc:
        st.error(f"Analysis could not be completed: {exc}")

if st.session_state.analysis is None:
    st.info(UI_TEXT["ready_to_analyze"])
    st.stop()

analysis = st.session_state.analysis
clean_df = st.session_state.clean_df
metrics = analysis["metrics"]
interpretation = hydrogeology_interpretation(metrics)

st.subheader(UI_TEXT["result_dashboard"])
metric_cols = st.columns(8)
metric_cols[0].metric(UI_TEXT["total_rainfall"], f"{metrics['total_rainfall_mm']:.1f} mm")
metric_cols[1].metric(UI_TEXT["mean_discharge"], f"{metrics['mean_discharge_m3s']:.3f}")
metric_cols[2].metric(UI_TEXT["max_discharge"], f"{metrics['max_discharge_m3s']:.3f}")
metric_cols[3].metric(UI_TEXT["min_discharge"], f"{metrics['min_discharge_m3s']:.3f}")
metric_cols[4].metric(UI_TEXT["estimated_lag"], f"{metrics['estimated_lag_days']} d")
metric_cols[5].metric(UI_TEXT["best_correlation"], f"{metrics['estimated_lag_correlation']:.3f}")
metric_cols[6].metric(UI_TEXT["rainfall_peaks"], str(metrics["rainfall_peak_count"]))
metric_cols[7].metric(UI_TEXT["discharge_peaks_short"], str(metrics["discharge_peak_count"]))

tabs = st.tabs(UI_TEXT["tabs"])

with tabs[0]:
    fig = plot_time_series(clean_df, controls["rolling_window"], controls["show_rolling"], controls["normalize"])
    show_plotly_figure(fig, "time_series", controls["plot_dragmode"])
    figure_download_controls(fig, "time_series")

with tabs[1]:
    fig = plot_time_series(
        clean_df,
        controls["rolling_window"],
        controls["show_rolling"],
        controls["normalize"],
        discharge_axis_type="log",
    )
    if (clean_df["spring_discharge_m3s"] <= 0).any() or controls["normalize"]:
        st.caption("Non-positive plotted discharge values are hidden on the log axis.")
    show_plotly_figure(fig, "time_series_log_y", controls["plot_dragmode"])
    figure_download_controls(fig, "time_series_log_y")

with tabs[2]:
    fig = plot_lag(analysis["lag_df"])
    show_plotly_figure(fig, "lag_correlation", controls["plot_dragmode"])
    st.dataframe(analysis["lag_df"], width="stretch")
    figure_download_controls(fig, "lag_correlation")

with tabs[3]:
    fig = plot_scatter(clean_df, controls["normalize"])
    show_plotly_figure(fig, "rainfall_discharge_scatter", controls["plot_dragmode"])
    figure_download_controls(fig, "rainfall_discharge_scatter")

with tabs[4]:
    fig = plot_distribution(clean_df)
    show_plotly_figure(fig, "discharge_histogram", controls["plot_dragmode"])
    rolling_fig = plot_rolling(clean_df, controls["rolling_window"])
    show_plotly_figure(rolling_fig, "rolling_discharge", controls["plot_dragmode"])
    figure_download_controls(fig, "discharge_histogram")
    figure_download_controls(rolling_fig, "rolling_discharge")

with tabs[5]:
    fig = plot_peaks(clean_df, analysis["rainfall_events"], analysis["discharge_peaks"])
    show_plotly_figure(fig, "peak_events", controls["plot_dragmode"])
    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(f"**{UI_TEXT['rainfall_peak_events']}**")
        st.dataframe(analysis["rainfall_events"], width="stretch")
    with col_right:
        st.markdown(f"**{UI_TEXT['discharge_peak_events']}**")
        st.dataframe(analysis["discharge_peaks"], width="stretch")
    figure_download_controls(fig, "peak_events")

with tabs[6]:
    st.markdown(f"### {UI_TEXT['hydrogeological_interpretation']}")
    st.write(interpretation)
    st.caption(UI_TEXT["interpretation_caption"])

    report_md = build_markdown_report(clean_df, analysis, st.session_state.params, interpretation)
    report_html = markdown_to_html(report_md)
    metrics_json = json.dumps(metrics, indent=2)
    metrics_csv = pd.DataFrame([metrics]).to_csv(index=False)

    export_cols = st.columns(3)
    export_cols[0].download_button("Cleaned data CSV", dataframe_to_csv_bytes(clean_df), "cleaned_karst_timeseries.csv", "text/csv", width="stretch")
    export_cols[1].download_button("Lag results CSV", dataframe_to_csv_bytes(analysis["lag_df"]), "lag_correlation_results.csv", "text/csv", width="stretch")
    export_cols[2].download_button("Metrics CSV", metrics_csv.encode("utf-8"), "summary_metrics.csv", "text/csv", width="stretch")

    export_cols_2 = st.columns(3)
    export_cols_2[0].download_button("Metrics JSON", metrics_json.encode("utf-8"), "summary_metrics.json", "application/json", width="stretch")
    export_cols_2[1].download_button("Markdown report", report_md.encode("utf-8"), "karst_analysis_report.md", "text/markdown", width="stretch")
    export_cols_2[2].download_button("HTML report", report_html.encode("utf-8"), "karst_analysis_report.html", "text/html", width="stretch")

    with st.expander(UI_TEXT["report_preview"], expanded=True):
        st.markdown(report_md)
