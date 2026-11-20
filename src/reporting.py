from __future__ import annotations

from typing import Any

import pandas as pd

from src.plot_config import load_plot_config


def hydrogeology_interpretation(metrics: dict[str, Any]) -> str:
    """Create cautious exploratory hydrogeological interpretation text."""
    lag = metrics["estimated_lag_days"]
    corr = metrics["estimated_lag_corr"]
    same_day_corr = metrics["rainfall_discharge_corr"]

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
    metrics: dict[str, Any],
    params: dict[str, Any],
    interpretation: str,
) -> str:
    """Build a downloadable Markdown analysis report."""
    start_date = df["date"].min().date()
    end_date = df["date"].max().date()

    metric_lines = "\n".join(
        [
            f"- Total rainfall: {metrics['total_rainfall_mm']:.2f} mm",
            f"- Mean discharge: {metrics['mean_discharge_m3s']:.3f} m3/s",
            f"- Maximum discharge: {metrics['max_discharge_m3s']:.3f} m3/s",
            f"- Minimum discharge: {metrics['min_discharge_m3s']:.3f} m3/s",
            f"- Estimated lag time: {metrics['estimated_lag_days']} days",
            f"- Highest lag correlation: {metrics['estimated_lag_corr']:.3f}",
            f"- Same-day correlation: {metrics['rainfall_discharge_corr']:.3f}",
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

This tool is intended for hydrogeological decision support, exploratory analysis, and visualization. It does not produce a standalone definitive hydrogeological model result. Field geology, recharge area definition, data quality, evapotranspiration, snowmelt, abstraction, and monitoring uncertainty should be evaluated separately.
"""


def markdown_to_html(
    markdown_text: str,
    config: dict[str, Any] | None = None,
) -> str:
    """Render Markdown text as a standalone HTML report styled from central config."""
    cfg = config if config is not None else load_plot_config()
    colors = cfg["colors"]
    typo = cfg["typography"]

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
    body {{
      font-family: "{typo['font_family']}", sans-serif;
      max-width: 920px;
      margin: 40px auto;
      line-height: 1.55;
      background: {colors['background']};
      color: {colors['text']};
    }}
    h1, h2 {{ color: {colors['heading']}; }}
    code {{ background: {colors['code_background']}; padding: 2px 4px; }}
  </style>
</head>
<body>{body}</body>
</html>
"""
