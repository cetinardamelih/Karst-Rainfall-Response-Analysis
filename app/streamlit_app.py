from __future__ import annotations

from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analysis import basic_statistics, build_analysis_summary
from src.data_loader import infer_column, map_input_columns
from src.interactive_charts import (
    PLOT_DRAG_MODES,
    get_plotly_chart_config,
    plot_distribution,
    plot_lag,
    plot_peaks,
    plot_rolling,
    plot_scatter,
    plot_time_series,
)
from src.plot_config import (
    FONT_FAMILY_OPTIONS,
    LEGEND_POSITION_OPTIONS,
    LINESTYLE_OPTIONS,
    MARKER_OPTIONS,
    RAINFALL_DISPLAY_OPTIONS,
    dump_plot_config_json,
    dump_plot_config_yaml,
    load_plot_config,
    parse_plot_config_bytes,
)
from src.preprocessing import MISSING_METHODS, clean_timeseries, filter_date_range
from src.reporting import build_markdown_report, hydrogeology_interpretation, markdown_to_html
from src.synthetic_data import generate_synthetic_karst_data
from src.ui_config import UI_TEXT


st.set_page_config(page_title=str(UI_TEXT["app_title"]), layout="wide")


# ---------------------------------------------------------------------------
# Cached data & analysis helpers
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def cached_sample_data() -> pd.DataFrame:
    return generate_synthetic_karst_data(periods=365, seed=42)


@st.cache_data(show_spinner=False)
def cached_read_csv(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_csv(BytesIO(file_bytes))


@st.cache_data(show_spinner=False)
def cached_clean_data(mapped_df: pd.DataFrame, missing_method: str) -> pd.DataFrame:
    return clean_timeseries(mapped_df, missing_method=missing_method)


@st.cache_data(show_spinner=False)
def cached_run_analysis(
    clean_df: pd.DataFrame,
    max_lag_days: int,
    rainfall_percentile: float,
    discharge_prominence: float | None,
    peak_distance_days: int,
) -> dict[str, Any]:
    summary, lag_df, rainfall_events, discharge_peaks = build_analysis_summary(
        clean_df,
        max_lag_days=max_lag_days,
        rainfall_percentile=rainfall_percentile,
        discharge_prominence=discharge_prominence,
        peak_distance_days=peak_distance_days,
    )
    return {
        "metrics": summary.to_dict(),
        "lag_df": lag_df,
        "rainfall_events": rainfall_events,
        "discharge_peaks": discharge_peaks,
        "statistics": basic_statistics(clean_df),
    }


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def initialize_state() -> None:
    defaults: dict[str, Any] = {
        "raw_df": None,
        "clean_df": None,
        "analysis": None,
        "params": {},
        "data_source": "sample",
        "plot_config": load_plot_config(),
        "cosmetic_version": 0,
        "last_uploaded_config": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = deepcopy(value) if isinstance(value, dict) else value


# ---------------------------------------------------------------------------
# Live cosmetic sidebar panel (reads & updates central plot_config)
# ---------------------------------------------------------------------------

def _safe_index(options: tuple[str, ...], value: str) -> int:
    return options.index(value) if value in options else 0


def render_cosmetic_sidebar() -> dict[str, Any]:
    """Render the live Cosmetic & Plot Settings panel in the sidebar."""
    cfg = deepcopy(st.session_state.plot_config)
    v = st.session_state.cosmetic_version

    with st.sidebar.expander(str(UI_TEXT["cosmetic_panel_title"]), expanded=False):
        st.caption("Varsayılanlar `config/plot_config.yaml` dosyasından okunur; değişiklikler anlık uygulanır.")

        uploaded_cfg = st.file_uploader(
            "Config Yükle (YAML / JSON)",
            type=["yaml", "yml", "json"],
            key=f"cfg_upload_{v}",
        )
        if uploaded_cfg is not None:
            token = (uploaded_cfg.name, uploaded_cfg.size)
            if st.session_state.last_uploaded_config != token:
                try:
                    st.session_state.plot_config = parse_plot_config_bytes(
                        uploaded_cfg.getvalue(),
                        uploaded_cfg.name,
                    )
                    st.session_state.last_uploaded_config = token
                    st.session_state.cosmetic_version += 1
                    st.rerun()
                except Exception as exc:
                    st.error(f"Config okunamadı: {exc}")

        if st.button("Varsayılanlara Sıfırla", width="stretch", key=f"cfg_reset_{v}"):
            st.session_state.plot_config = load_plot_config()
            st.session_state.last_uploaded_config = None
            st.session_state.cosmetic_version += 1
            st.rerun()

        # --- Colors ---
        st.markdown("**Renk Paleti**")
        c = cfg["colors"]
        col1, col2 = st.columns(2)
        c["rainfall"] = col1.color_picker("Yağış", c["rainfall"], key=f"c_rain_{v}")
        c["discharge"] = col2.color_picker("Debi", c["discharge"], key=f"c_dis_{v}")
        c["temperature"] = col1.color_picker("Sıcaklık", c["temperature"], key=f"c_temp_{v}")
        c["rolling_mean"] = col2.color_picker("Hareketli Ort.", c["rolling_mean"], key=f"c_roll_{v}")
        c["rainfall_peak"] = col1.color_picker("Yağış Piki", c["rainfall_peak"], key=f"c_rpk_{v}")
        c["discharge_peak"] = col2.color_picker("Debi Piki", c["discharge_peak"], key=f"c_dpk_{v}")
        c["lag_correlation"] = col1.color_picker("Gecikme Kor.", c["lag_correlation"], key=f"c_lag_{v}")
        c["scatter_points"] = col2.color_picker("Scatter", c["scatter_points"], key=f"c_scat_{v}")
        c["background"] = col1.color_picker("Arka Plan", c["background"], key=f"c_bg_{v}")
        c["plot_background"] = col2.color_picker("Grafik Alanı", c["plot_background"], key=f"c_pbg_{v}")
        c["grid"] = col1.color_picker("Grid", c["grid"], key=f"c_grid_{v}")
        c["text"] = col2.color_picker("Metin", c["text"], key=f"c_txt_{v}")
        c["heading"] = c["text"]

        # --- Shapes & Styles ---
        st.markdown("**Şekiller ve Stiller**")
        s = cfg["styles"]
        s["rainfall_display"] = st.selectbox(
            "Yağış görünümü",
            RAINFALL_DISPLAY_OPTIONS,
            index=_safe_index(RAINFALL_DISPLAY_OPTIONS, s["rainfall_display"]),
            key=f"s_rdisp_{v}",
        )
        s["rainfall_alpha"] = st.slider(
            "Yağış şeffaflık (alpha)", 0.10, 1.00, float(s["rainfall_alpha"]), 0.05, key=f"s_ralpha_{v}"
        )
        s["discharge_linewidth"] = st.slider(
            "Debi çizgi kalınlığı", 0.5, 5.0, float(s["discharge_linewidth"]), 0.1, key=f"s_dlw_{v}"
        )
        s["discharge_linestyle"] = st.selectbox(
            "Debi çizgi tipi",
            LINESTYLE_OPTIONS,
            index=_safe_index(LINESTYLE_OPTIONS, s["discharge_linestyle"]),
            key=f"s_dls_{v}",
        )
        s["discharge_alpha"] = st.slider(
            "Debi şeffaflık (alpha)", 0.20, 1.00, float(s["discharge_alpha"]), 0.05, key=f"s_dalpha_{v}"
        )
        s["rolling_linestyle"] = st.selectbox(
            "Hareketli ort. çizgi tipi",
            LINESTYLE_OPTIONS,
            index=_safe_index(LINESTYLE_OPTIONS, s["rolling_linestyle"]),
            key=f"s_rls_{v}",
        )
        s["discharge_peak_marker"] = st.selectbox(
            "Debi pik marker şekli",
            MARKER_OPTIONS,
            index=_safe_index(MARKER_OPTIONS, s["discharge_peak_marker"]),
            key=f"s_dpm_{v}",
        )
        s["rainfall_peak_marker"] = st.selectbox(
            "Yağış pik marker şekli",
            MARKER_OPTIONS,
            index=_safe_index(MARKER_OPTIONS, s["rainfall_peak_marker"]),
            key=f"s_rpm_{v}",
        )
        peak_size = st.slider(
            "Pik marker boyutu", 5, 20, int(s["discharge_peak_marker_size"]), 1, key=f"s_pms_{v}"
        )
        s["discharge_peak_marker_size"] = peak_size
        s["rainfall_peak_marker_size"] = peak_size
        s["scatter_marker"] = st.selectbox(
            "Scatter marker şekli",
            MARKER_OPTIONS,
            index=_safe_index(MARKER_OPTIONS, s["scatter_marker"]),
            key=f"s_sm_{v}",
        )
        s["scatter_marker_size"] = st.slider(
            "Scatter marker boyutu", 3, 16, int(s["scatter_marker_size"]), 1, key=f"s_sms_{v}"
        )
        s["scatter_alpha"] = st.slider(
            "Scatter şeffaflık", 0.15, 1.00, float(s["scatter_alpha"]), 0.05, key=f"s_salpha_{v}"
        )

        # --- Typography ---
        st.markdown("**Tipografi**")
        t = cfg["typography"]
        t["font_family"] = st.selectbox(
            "Font ailesi",
            FONT_FAMILY_OPTIONS,
            index=_safe_index(FONT_FAMILY_OPTIONS, t["font_family"]),
            key=f"t_ff_{v}",
        )
        t["title_size"] = st.slider("Başlık boyutu", 10, 26, int(t["title_size"]), 1, key=f"t_ts_{v}")
        t["axis_label_size"] = st.slider("Eksen başlığı boyutu", 8, 20, int(t["axis_label_size"]), 1, key=f"t_as_{v}")
        t["tick_size"] = st.slider("Tick (sayı) boyutu", 7, 18, int(t["tick_size"]), 1, key=f"t_tks_{v}")
        t["legend_size"] = st.slider("Lejant boyutu", 7, 18, int(t["legend_size"]), 1, key=f"t_lgs_{v}")

        # --- Layout & Performance ---
        st.markdown("**Yerleşim & Performans**")
        lay = cfg["layout"]
        lay["show_grid"] = st.checkbox("Grid çizgilerini göster", value=bool(lay["show_grid"]), key=f"l_grid_{v}")
        lay["grid_alpha"] = st.slider("Grid şeffaflığı", 0.05, 1.00, float(lay["grid_alpha"]), 0.05, key=f"l_ga_{v}")
        lay["show_legend"] = st.checkbox("Lejantı göster", value=bool(lay["show_legend"]), key=f"l_leg_{v}")
        lay["legend_position"] = st.selectbox(
            "Lejant konumu",
            LEGEND_POSITION_OPTIONS,
            index=_safe_index(LEGEND_POSITION_OPTIONS, lay["legend_position"]),
            key=f"l_lpos_{v}",
        )
        lay["show_temperature"] = st.checkbox(
            "Sıcaklık alt grafiğini göster", value=bool(lay["show_temperature"]), key=f"l_temp_{v}"
        )
        lay["show_peaks_on_timeseries"] = st.checkbox(
            "Zaman serisinde pikleri işaretle", value=bool(lay["show_peaks_on_timeseries"]), key=f"l_pks_{v}"
        )
        lay["interactive_height"] = st.slider(
            "Grafik yüksekliği (px)", 360, 800, int(lay["interactive_height"]), 20, key=f"l_ih_{v}"
        )

        perf = cfg["performance"]
        perf["use_webgl"] = st.checkbox("WebGL hızlandırma (Scattergl)", value=bool(perf["use_webgl"]), key=f"p_gl_{v}")
        perf["downsample_threshold"] = st.number_input(
            "LTTB eşik satır sayısı", min_value=500, max_value=50000, value=int(perf["downsample_threshold"]), step=500, key=f"p_dt_{v}"
        )
        perf["downsample_target_points"] = st.number_input(
            "LTTB hedef nokta sayısı", min_value=300, max_value=10000, value=int(perf["downsample_target_points"]), step=100, key=f"p_tp_{v}"
        )
        perf["show_rangeslider"] = st.checkbox(
            "Alt aralık kaydırıcısı (uzun seride yavaşlatır)",
            value=bool(perf["show_rangeslider"]),
            key=f"p_rs_{v}",
        )

        st.divider()
        st.markdown("**Ayarları Config Olarak İndir**")
        dl1, dl2 = st.columns(2)
        dl1.download_button(
            "YAML İndir",
            data=dump_plot_config_yaml(cfg).encode("utf-8"),
            file_name="plot_config.yaml",
            mime="text/yaml",
            width="stretch",
        )
        dl2.download_button(
            "JSON İndir",
            data=dump_plot_config_json(cfg).encode("utf-8"),
            file_name="plot_config.json",
            mime="application/json",
            width="stretch",
        )

    st.session_state.plot_config = cfg
    return cfg


# ---------------------------------------------------------------------------
# UI rendering helpers
# ---------------------------------------------------------------------------

def render_figure(
    fig: go.Figure,
    key: str,
    config: dict[str, Any],
    *,
    was_downsampled: bool = False,
    total_rows: int = 0,
) -> None:
    """Render an interactive WebGL Plotly chart with lazy download controls."""
    st.plotly_chart(
        fig,
        width="stretch",
        config=get_plotly_chart_config(config),
        key=key,
    )
    if was_downsampled:
        target = config["performance"]["downsample_target_points"]
        st.caption(
            f"WebGL + pik korumalı LTTB aktif ({total_rows:,} günden ~{target:,} temsili nokta + tüm pikler çizildi)."
        )

    with st.expander("Grafiği Dışa Aktar (HTML / PNG)", expanded=False):
        if st.checkbox("İndirme dosyalarını hazırla", key=f"prep_export_{key}", value=False):
            col_html, col_png = st.columns(2)
            html_bytes = fig.to_html(full_html=True, include_plotlyjs="cdn").encode("utf-8")
            col_html.download_button(
                "Etkileşimli HTML İndir",
                data=html_bytes,
                file_name=f"{key}.html",
                mime="text/html",
                width="stretch",
                key=f"dl_html_{key}",
            )
            try:
                scale = int(config["performance"]["export_image_scale"])
                png_bytes = fig.to_image(format="png", scale=scale)
                col_png.download_button(
                    "PNG İndir",
                    data=png_bytes,
                    file_name=f"{key}.png",
                    mime="image/png",
                    width="stretch",
                    key=f"dl_png_{key}",
                )
            except Exception:
                col_png.caption("PNG çıktısı için opsiyonel `kaleido` paketi gerekir (grafik üstündeki kamera ikonu tarayıcıdan doğrudan PNG kaydeder).")


def render_analysis_sidebar(raw_df: pd.DataFrame) -> dict[str, Any]:
    """Render column mapping, preprocessing, and analysis parameter controls."""
    st.sidebar.header(str(UI_TEXT["column_mapping"]))
    columns = raw_df.columns.tolist()

    inferred_date = infer_column(columns, ["date", "time"])
    inferred_rain = infer_column(columns, ["rainfall", "precip", "rain"])
    inferred_discharge = infer_column(columns, ["discharge", "flow", "spring"])
    inferred_temp = infer_column(columns, ["temperature", "temp"])

    date_col = st.sidebar.selectbox(
        str(UI_TEXT["date_column"]),
        columns,
        index=columns.index(inferred_date) if inferred_date in columns else 0,
    )
    rainfall_col = st.sidebar.selectbox(
        str(UI_TEXT["rainfall_column"]),
        columns,
        index=columns.index(inferred_rain) if inferred_rain in columns else 0,
    )
    discharge_col = st.sidebar.selectbox(
        str(UI_TEXT["discharge_column"]),
        columns,
        index=columns.index(inferred_discharge) if inferred_discharge in columns else 0,
    )
    temp_options = ["None"] + columns
    temperature_col = st.sidebar.selectbox(
        str(UI_TEXT["temperature_column"]),
        temp_options,
        index=temp_options.index(inferred_temp) if inferred_temp in temp_options else 0,
    )

    st.sidebar.header(str(UI_TEXT["preprocessing"]))
    cleaning_method = st.sidebar.radio(str(UI_TEXT["missing_value_handling"]), list(MISSING_METHODS), index=0)

    st.sidebar.header(str(UI_TEXT["analysis_settings"]))
    max_lag_days = st.sidebar.slider(str(UI_TEXT["max_lag_days"]), 3, 60, 14)
    rainfall_percentile = st.sidebar.slider(str(UI_TEXT["rainfall_peak_percentile"]), 70.0, 99.0, 90.0, 1.0)
    use_auto_prominence = st.sidebar.checkbox(str(UI_TEXT["auto_discharge_peak_prominence"]), value=True)
    discharge_prominence = (
        None
        if use_auto_prominence
        else st.sidebar.number_input(str(UI_TEXT["minimum_discharge_peak_prominence"]), min_value=0.0, value=0.5, step=0.1)
    )
    peak_distance_days = st.sidebar.slider(str(UI_TEXT["minimum_distance_between_peaks"]), 1, 30, 3)
    rolling_window = st.sidebar.slider(str(UI_TEXT["rolling_average_window"]), 1, 30, 7)
    show_rolling = st.sidebar.checkbox(str(UI_TEXT["show_rolling_average"]), value=True)
    normalize = st.sidebar.checkbox(str(UI_TEXT["normalize_charts"]), value=False)
    plot_mode_label = st.sidebar.selectbox(str(UI_TEXT["plot_interaction_mode"]), list(PLOT_DRAG_MODES.keys()), index=0)

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


# ---------------------------------------------------------------------------
# Main application flow
# ---------------------------------------------------------------------------

def main() -> None:
    initialize_state()

    st.title(str(UI_TEXT["app_title"]))
    st.write(str(UI_TEXT["app_intro"]))
    st.info(str(UI_TEXT["decision_support_note"]))
    steps = list(UI_TEXT["workflow_steps"])
    for col, label in zip(st.columns(len(steps)), steps):
        col.markdown(f"**{label}**")

    # Sidebar: data source
    st.sidebar.header(str(UI_TEXT["data_source"]))
    uploaded_file = st.sidebar.file_uploader(str(UI_TEXT["upload_csv"]), type=["csv"])
    use_sample = st.sidebar.button(str(UI_TEXT["load_sample_dataset"]), width="stretch")

    sample_df = cached_sample_data()
    st.sidebar.download_button(
        str(UI_TEXT["download_sample_csv"]),
        data=dataframe_to_csv_bytes(sample_df),
        file_name="synthetic_karst_timeseries.csv",
        mime="text/csv",
        width="stretch",
    )

    with st.expander(str(UI_TEXT["example_csv_format"]), expanded=False):
        st.dataframe(sample_df.head(5), width="stretch")

    if uploaded_file is not None:
        try:
            st.session_state.raw_df = cached_read_csv(uploaded_file.getvalue())
            st.session_state.data_source = "uploaded"
        except Exception as exc:
            st.error(f"CSV could not be read: {exc}")
    elif use_sample or st.session_state.raw_df is None:
        st.session_state.raw_df = sample_df
        st.session_state.data_source = "sample"

    raw_df = st.session_state.raw_df
    if raw_df is None or raw_df.empty:
        st.warning(str(UI_TEXT["load_data_to_begin"]))
        st.stop()

    controls = render_analysis_sidebar(raw_df)
    plot_config = render_cosmetic_sidebar()

    # Preview & column mapping
    st.subheader(str(UI_TEXT["data_preview"]))
    source_label = UI_TEXT["uploaded_csv"] if st.session_state.data_source == "uploaded" else UI_TEXT["sample_dataset"]
    st.caption(f"{UI_TEXT['current_source']}: {source_label}")
    st.dataframe(raw_df.head(10), width="stretch")

    col_missing, col_shape, col_parse = st.columns(3)
    col_shape.metric(str(UI_TEXT["rows"]), f"{len(raw_df):,}")
    col_shape.metric(str(UI_TEXT["columns"]), f"{len(raw_df.columns):,}")
    col_missing.metric(str(UI_TEXT["missing_cells"]), f"{int(raw_df.isna().sum().sum()):,}")
    parse_rate = pd.to_datetime(raw_df[controls["date_col"]], errors="coerce").notna().mean() * 100
    col_parse.metric(str(UI_TEXT["date_parse_success"]), f"{parse_rate:.1f}%")

    with st.expander(str(UI_TEXT["missing_value_report"]), expanded=False):
        missing_report = raw_df.isna().sum().rename("missing_count").reset_index().rename(columns={"index": "column"})
        st.dataframe(missing_report, width="stretch")

    try:
        mapped_df = map_input_columns(
            raw_df,
            controls["date_col"],
            controls["rainfall_col"],
            controls["discharge_col"],
            controls["temperature_col"],
        )
    except Exception as exc:
        st.error(f"Column mapping failed: {exc}")
        st.stop()

    if int((mapped_df["rainfall_mm"] < 1.0).sum()):
        st.warning("Rainfall values below 1.0 mm detected; cleaning sets trace rainfall to zero.")
    if int((mapped_df["spring_discharge_m3s"] < 0).sum()):
        st.warning("Negative discharge values detected; cleaning clips discharge at zero.")

    clean_df = cached_clean_data(mapped_df, controls["cleaning_method"])
    if clean_df.empty:
        st.error("No valid rows remain after preprocessing. Check column mapping and missing values.")
        st.stop()

    date_min, date_max = clean_df["date"].min().date(), clean_df["date"].max().date()
    selected_range = st.sidebar.date_input(
        str(UI_TEXT["date_range"]),
        value=(date_min, date_max),
        min_value=date_min,
        max_value=date_max,
    )
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        clean_df = filter_date_range(clean_df, pd.Timestamp(selected_range[0]), pd.Timestamp(selected_range[1]))

    if len(clean_df) < controls["max_lag_days"] + 5:
        st.warning("Selected date range is short relative to max lag days.")

    st.subheader(str(UI_TEXT["preprocessing_check"]))
    chk = st.columns(4)
    chk[0].metric(str(UI_TEXT["clean_rows"]), f"{len(clean_df):,}")
    chk[1].metric(str(UI_TEXT["start_date"]), str(clean_df["date"].min().date()))
    chk[2].metric(str(UI_TEXT["end_date"]), str(clean_df["date"].max().date()))
    chk[3].metric(str(UI_TEXT["remaining_missing"]), f"{int(clean_df.isna().sum().sum()):,}")

    if st.button(str(UI_TEXT["run_analysis"]), type="primary", width="stretch"):
        try:
            st.session_state.clean_df = clean_df
            st.session_state.analysis = cached_run_analysis(
                clean_df,
                controls["max_lag_days"],
                controls["rainfall_percentile"],
                controls["discharge_prominence"],
                controls["peak_distance_days"],
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
            st.success(str(UI_TEXT["analysis_completed"]))
        except Exception as exc:
            st.error(f"Analysis could not be completed: {exc}")

    if st.session_state.analysis is None:
        st.info(str(UI_TEXT["ready_to_analyze"]))
        st.stop()

    analysis = st.session_state.analysis
    active_df = st.session_state.clean_df
    metrics = analysis["metrics"]
    interpretation = hydrogeology_interpretation(metrics)
    dragmode = controls["plot_dragmode"]

    # Dashboard metrics
    st.subheader(str(UI_TEXT["result_dashboard"]))
    mc = st.columns(8)
    mc[0].metric(str(UI_TEXT["total_rainfall"]), f"{metrics['total_rainfall_mm']:.1f} mm")
    mc[1].metric(str(UI_TEXT["mean_discharge"]), f"{metrics['mean_discharge_m3s']:.3f}")
    mc[2].metric(str(UI_TEXT["max_discharge"]), f"{metrics['max_discharge_m3s']:.3f}")
    mc[3].metric(str(UI_TEXT["min_discharge"]), f"{metrics['min_discharge_m3s']:.3f}")
    mc[4].metric(str(UI_TEXT["estimated_lag"]), f"{metrics['estimated_lag_days']} d")
    mc[5].metric(str(UI_TEXT["best_correlation"]), f"{metrics['estimated_lag_corr']:.3f}")
    mc[6].metric(str(UI_TEXT["rainfall_peaks"]), str(metrics["rainfall_peak_count"]))
    mc[7].metric(str(UI_TEXT["discharge_peaks_short"]), str(metrics["discharge_peak_count"]))

    tabs = st.tabs(list(UI_TEXT["tabs"]))

    with tabs[0]:
        fig, ds = plot_time_series(
            active_df,
            plot_config,
            rolling_window=controls["rolling_window"],
            show_rolling=controls["show_rolling"],
            normalize=controls["normalize"],
            rainfall_events=analysis["rainfall_events"],
            discharge_peaks=analysis["discharge_peaks"],
            dragmode=dragmode,
        )
        render_figure(fig, "time_series", plot_config, was_downsampled=ds, total_rows=len(active_df))

    with tabs[1]:
        fig, ds = plot_time_series(
            active_df,
            plot_config,
            rolling_window=controls["rolling_window"],
            show_rolling=controls["show_rolling"],
            normalize=controls["normalize"],
            discharge_axis_type="log",
            rainfall_events=analysis["rainfall_events"],
            discharge_peaks=analysis["discharge_peaks"],
            dragmode=dragmode,
        )
        if (active_df["spring_discharge_m3s"] <= 0).any() or controls["normalize"]:
            st.caption("Non-positive plotted discharge values are hidden on the logarithmic axis.")
        render_figure(fig, "time_series_log_y", plot_config, was_downsampled=ds, total_rows=len(active_df))

    with tabs[2]:
        fig = plot_lag(analysis["lag_df"], plot_config, dragmode=dragmode)
        render_figure(fig, "lag_correlation", plot_config)
        st.dataframe(analysis["lag_df"], width="stretch")

    with tabs[3]:
        fig = plot_scatter(active_df, plot_config, normalize=controls["normalize"], dragmode=dragmode)
        render_figure(fig, "rainfall_discharge_scatter", plot_config)

    with tabs[4]:
        fig_hist = plot_distribution(active_df, plot_config, dragmode=dragmode)
        render_figure(fig_hist, "discharge_histogram", plot_config)
        fig_roll, ds_roll = plot_rolling(
            active_df,
            plot_config,
            rolling_window=controls["rolling_window"],
            dragmode=dragmode,
        )
        render_figure(fig_roll, "rolling_discharge", plot_config, was_downsampled=ds_roll, total_rows=len(active_df))

    with tabs[5]:
        fig_peaks, ds_peaks = plot_peaks(
            active_df,
            analysis["rainfall_events"],
            analysis["discharge_peaks"],
            plot_config,
            dragmode=dragmode,
        )
        render_figure(fig_peaks, "peak_events", plot_config, was_downsampled=ds_peaks, total_rows=len(active_df))
        left, right = st.columns(2)
        left.markdown(f"**{UI_TEXT['rainfall_peak_events']}**")
        left.dataframe(analysis["rainfall_events"], width="stretch")
        right.markdown(f"**{UI_TEXT['discharge_peak_events']}**")
        right.dataframe(analysis["discharge_peaks"], width="stretch")

    with tabs[6]:
        st.markdown(f"### {UI_TEXT['hydrogeological_interpretation']}")
        st.write(interpretation)
        st.caption(str(UI_TEXT["interpretation_caption"]))

        report_md = build_markdown_report(active_df, metrics, st.session_state.params, interpretation)
        report_html = markdown_to_html(report_md, plot_config)
        metrics_json = json.dumps(metrics, indent=2)
        metrics_csv = pd.DataFrame([metrics]).to_csv(index=False)

        r1 = st.columns(3)
        r1[0].download_button("Cleaned data CSV", dataframe_to_csv_bytes(active_df), "cleaned_karst_timeseries.csv", "text/csv", width="stretch")
        r1[1].download_button("Lag results CSV", dataframe_to_csv_bytes(analysis["lag_df"]), "lag_correlation_results.csv", "text/csv", width="stretch")
        r1[2].download_button("Metrics CSV", metrics_csv.encode("utf-8"), "summary_metrics.csv", "text/csv", width="stretch")

        r2 = st.columns(3)
        r2[0].download_button("Metrics JSON", metrics_json.encode("utf-8"), "summary_metrics.json", "application/json", width="stretch")
        r2[1].download_button("Markdown report", report_md.encode("utf-8"), "karst_analysis_report.md", "text/markdown", width="stretch")
        r2[2].download_button("HTML report", report_html.encode("utf-8"), "karst_analysis_report.html", "text/html", width="stretch")

        with st.expander(str(UI_TEXT["report_preview"]), expanded=True):
            st.markdown(report_md)


if __name__ == "__main__":
    main()
