from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - optional fallback if PyYAML is absent.
    yaml = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "plot_config.yaml"

LINESTYLE_OPTIONS = ("solid", "dashed", "dotted", "dashdot")
MARKER_OPTIONS = ("circle", "triangle-down", "triangle-up", "diamond", "square", "cross", "x")
LEGEND_POSITION_OPTIONS = ("upper left", "upper right", "lower left", "lower right", "top", "bottom")
FONT_FAMILY_OPTIONS = (
    "DejaVu Sans",
    "Arial",
    "Helvetica",
    "Georgia",
    "Times New Roman",
    "Courier New",
)
RAINFALL_DISPLAY_OPTIONS = ("bar", "line")

LINESTYLE_TO_MPL: dict[str, str] = {
    "solid": "-",
    "dashed": "--",
    "dotted": ":",
    "dashdot": "-.",
}

LINESTYLE_TO_PLOTLY: dict[str, str] = {
    "solid": "solid",
    "dashed": "dash",
    "dotted": "dot",
    "dashdot": "dashdot",
}

MARKER_TO_MPL: dict[str, str] = {
    "circle": "o",
    "triangle-down": "v",
    "triangle-up": "^",
    "diamond": "D",
    "square": "s",
    "cross": "+",
    "x": "x",
}

MARKER_TO_PLOTLY: dict[str, str] = {
    "circle": "circle",
    "triangle-down": "triangle-down",
    "triangle-up": "triangle-up",
    "diamond": "diamond",
    "square": "square",
    "cross": "cross",
    "x": "x",
}

DEFAULT_PLOT_CONFIG: dict[str, Any] = {
    "colors": {
        "rainfall": "#0072B2",
        "rainfall_peak": "#56B4E9",
        "discharge": "#D55E00",
        "discharge_peak": "#CC0000",
        "temperature": "#E69F00",
        "rolling_mean": "#332288",
        "raw_discharge": "#999999",
        "lag_correlation": "#009E73",
        "scatter_points": "#882255",
        "reference_line": "#666666",
        "marker_edge": "#FFFFFF",
        "annotation_fill": "rgba(204, 0, 0, 0.12)",
        "background": "#FFFFFF",
        "plot_background": "#FFFFFF",
        "grid": "#CBD5E1",
        "text": "#1F2933",
        "heading": "#0F172A",
        "code_background": "#F3F4F6",
    },
    "styles": {
        "rainfall_display": "bar",
        "rainfall_bar_width": 1.0,
        "rainfall_linewidth": 1.4,
        "rainfall_linestyle": "solid",
        "rainfall_alpha": 0.40,
        "discharge_linewidth": 1.8,
        "discharge_linestyle": "solid",
        "discharge_alpha": 0.95,
        "temperature_linewidth": 1.4,
        "temperature_linestyle": "dashed",
        "temperature_alpha": 0.85,
        "rolling_linewidth": 2.2,
        "rolling_linestyle": "dotted",
        "rolling_alpha": 0.95,
        "raw_discharge_linewidth": 1.0,
        "raw_discharge_linestyle": "solid",
        "raw_discharge_alpha": 0.70,
        "lag_linewidth": 2.0,
        "lag_linestyle": "solid",
        "lag_marker": "circle",
        "lag_marker_size": 7,
        "lag_alpha": 0.95,
        "scatter_marker": "circle",
        "scatter_marker_size": 7,
        "scatter_alpha": 0.65,
        "scatter_edge_width": 0.4,
        "rainfall_peak_marker": "triangle-down",
        "rainfall_peak_marker_size": 10,
        "rainfall_peak_alpha": 0.95,
        "discharge_peak_marker": "diamond",
        "discharge_peak_marker_size": 10,
        "discharge_peak_alpha": 0.95,
        "reference_linewidth": 1.0,
        "reference_linestyle": "dashed",
        "reference_alpha": 0.60,
        "histogram_bins": 30,
        "histogram_alpha": 0.85,
        "annotation_linewidth": 2.5,
        "annotation_alpha": 0.85,
    },
    "typography": {
        "font_family": "DejaVu Sans",
        "title_size": 14,
        "axis_label_size": 11,
        "tick_size": 10,
        "legend_size": 10,
    },
    "layout": {
        "figsize_timeseries": [12.0, 6.0],
        "figsize_lag": [8.0, 5.0],
        "figsize_scatter": [7.5, 5.5],
        "figsize_histogram": [7.5, 5.5],
        "interactive_height": 540,
        "interactive_compact_height": 460,
        "dpi": 200,
        "save_formats": ["png"],
        "show_grid": True,
        "grid_alpha": 0.35,
        "grid_linestyle": "dashed",
        "grid_linewidth": 0.7,
        "show_legend": True,
        "legend_position": "upper left",
        "show_temperature": False,
        "show_peaks_on_timeseries": True,
        "labels": {
            "date_axis": "Date",
            "rainfall_axis": "Rainfall (mm/day)",
            "rainfall_normalized_axis": "Rainfall (normalized)",
            "discharge_axis": "Spring discharge (m³/s)",
            "discharge_log_axis": "Spring discharge (m³/s, log scale)",
            "discharge_normalized_axis": "Spring discharge (normalized)",
            "temperature_axis": "Mean temperature (°C)",
            "lag_axis": "Rainfall lag (days)",
            "correlation_axis": "Pearson correlation",
            "frequency_axis": "Frequency",
            "timeseries_title": "Karst Rainfall-Discharge Time Series",
            "timeseries_log_title": "Karst Rainfall-Discharge Time Series (Log Discharge Axis)",
            "lag_title": "Lagged Rainfall-Discharge Correlation",
            "scatter_title": "Rainfall-Discharge Scatter Plot",
            "histogram_title": "Spring Discharge Distribution",
            "rolling_title": "Rolling Mean Spring Discharge",
            "peaks_title": "Peak Rainfall and Discharge Events",
            "series_rainfall": "Rainfall",
            "series_discharge": "Discharge",
            "series_temperature": "Temperature",
            "series_rolling": "Rolling mean",
            "series_raw_discharge": "Daily discharge",
            "series_lag": "Lag correlation",
            "series_scatter": "Daily observations",
            "series_rainfall_peaks": "Rainfall peaks",
            "series_discharge_peaks": "Discharge peaks",
        },
    },
    "performance": {
        "use_webgl": True,
        "downsample_threshold": 2000,
        "downsample_target_points": 1500,
        "rainfall_stem_threshold": 800,
        "show_rangeslider": False,
        "export_image_scale": 2,
    },
}


def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override keys into a deep copy of base."""
    merged = deepcopy(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def load_plot_config(path: Path | str | None = None) -> dict[str, Any]:
    """Load cosmetic configuration from YAML/JSON, merged with built-in defaults."""
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return deepcopy(DEFAULT_PLOT_CONFIG)

    text = config_path.read_text(encoding="utf-8")
    if config_path.suffix.lower() == ".json":
        parsed = json.loads(text)
    elif yaml is not None:
        parsed = yaml.safe_load(text) or {}
    else:
        return deepcopy(DEFAULT_PLOT_CONFIG)

    if not isinstance(parsed, dict):
        raise ValueError(f"Plot config must be a mapping, got {type(parsed).__name__}.")
    return deep_merge(DEFAULT_PLOT_CONFIG, parsed)


def parse_plot_config_bytes(data: bytes, filename: str) -> dict[str, Any]:
    """Parse an uploaded YAML or JSON config payload and merge with defaults."""
    text = data.decode("utf-8")
    if filename.lower().endswith(".json"):
        parsed = json.loads(text)
    else:
        if yaml is None:
            raise RuntimeError("PyYAML is required to load YAML config files.")
        parsed = yaml.safe_load(text) or {}
    if not isinstance(parsed, dict):
        raise ValueError("Uploaded config must contain a top-level mapping.")
    return deep_merge(DEFAULT_PLOT_CONFIG, parsed)


def dump_plot_config_yaml(config: dict[str, Any]) -> str:
    """Serialize a plot configuration dictionary as readable YAML."""
    if yaml is not None:
        return yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    return dump_plot_config_json(config)


def dump_plot_config_json(config: dict[str, Any]) -> str:
    """Serialize a plot configuration dictionary as formatted JSON."""
    return json.dumps(config, indent=2, ensure_ascii=False)


def mpl_linestyle(name: str) -> str:
    """Convert canonical linestyle name to a Matplotlib linestyle string."""
    return LINESTYLE_TO_MPL.get(name, "-")


def plotly_linestyle(name: str) -> str:
    """Convert canonical linestyle name to a Plotly dash string."""
    return LINESTYLE_TO_PLOTLY.get(name, "solid")


def mpl_marker(name: str) -> str:
    """Convert canonical marker name to a Matplotlib marker code."""
    return MARKER_TO_MPL.get(name, "o")


def plotly_marker(name: str) -> str:
    """Convert canonical marker name to a Plotly symbol name."""
    return MARKER_TO_PLOTLY.get(name, "circle")


def mpl_legend_kwargs(config: dict[str, Any]) -> dict[str, Any]:
    """Build Matplotlib legend positioning arguments from central config."""
    pos = config["layout"]["legend_position"]
    fontsize = config["typography"]["legend_size"]
    base: dict[str, Any] = {
        "fontsize": fontsize,
        "frameon": True,
        "facecolor": config["colors"]["background"],
        "edgecolor": config["colors"]["grid"],
    }
    if pos == "top":
        base.update({"loc": "lower center", "bbox_to_anchor": (0.5, 1.02), "ncol": 4})
    elif pos == "bottom":
        base.update({"loc": "upper center", "bbox_to_anchor": (0.5, -0.15), "ncol": 4})
    else:
        base["loc"] = pos
    return base


def plotly_legend_dict(config: dict[str, Any]) -> dict[str, Any]:
    """Build Plotly legend layout dictionary from central config."""
    pos = config["layout"]["legend_position"]
    legend: dict[str, Any] = {
        "font": {
            "family": config["typography"]["font_family"],
            "size": config["typography"]["legend_size"],
            "color": config["colors"]["text"],
        },
        "bgcolor": hex_to_rgba(config["colors"]["background"], 0.80),
    }
    if pos == "top":
        legend.update({"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "center", "x": 0.5})
    elif pos == "bottom":
        legend.update({"orientation": "h", "yanchor": "top", "y": -0.18, "xanchor": "center", "x": 0.5})
    elif pos == "upper right":
        legend.update({"yanchor": "top", "y": 0.98, "xanchor": "right", "x": 0.98})
    elif pos == "lower left":
        legend.update({"yanchor": "bottom", "y": 0.02, "xanchor": "left", "x": 0.02})
    elif pos == "lower right":
        legend.update({"yanchor": "bottom", "y": 0.02, "xanchor": "right", "x": 0.98})
    else:  # upper left
        legend.update({"yanchor": "top", "y": 0.98, "xanchor": "left", "x": 0.02})
    return legend


def hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a #RRGGBB color string to an rgba(...) CSS string."""
    cleaned = hex_color.strip()
    if cleaned.startswith("rgba(") or cleaned.startswith("rgb("):
        return cleaned
    cleaned = cleaned.lstrip("#")
    if len(cleaned) != 6:
        return hex_color
    r, g, b = int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"
