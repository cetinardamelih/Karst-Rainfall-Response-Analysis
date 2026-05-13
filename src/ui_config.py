from __future__ import annotations

# Edit chart colors here. The palette uses high-contrast, colorblind-friendly
# tones so rainfall, discharge, peaks, and reference lines stay easy to tell apart.
CHART_COLORS = {
    "rainfall": "#0072B2",
    "rainfall_peak": "#56B4E9",
    "discharge": "#D55E00",
    "discharge_peak": "#CC0000",
    "lag_correlation": "#009E73",
    "scatter_points": "#882255",
    "rolling_mean": "#332288",
    "raw_discharge": "#999999",
    "reference_line": "#666666",
    "html_text": "#1F2933",
    "html_heading": "#0F172A",
    "code_background": "#F3F4F6",
}

# Edit visible Streamlit interface text here.
UI_TEXT = {
    "app_title": "Karst Rainfall-Response Analysis",
    "app_intro": (
        "A clean exploratory interface for analysing rainfall, lagged spring discharge response, "
        "peak events, and correlation patterns in karst hydrogeology datasets."
    ),
    "decision_support_note": (
        "This tool supports hydrogeological decision support and data exploration; "
        "it does not produce definitive model results by itself."
    ),
    "workflow_steps": [
        "1. Load data",
        "2. Map columns",
        "3. Run analysis",
        "4. Review results",
        "5. Download report",
    ],
    "column_mapping": "Column mapping",
    "date_column": "Date column",
    "rainfall_column": "Rainfall column",
    "discharge_column": "Discharge column",
    "temperature_column": "Temperature column (optional)",
    "preprocessing": "Preprocessing",
    "missing_value_handling": "Missing value handling",
    "analysis_settings": "Analysis settings",
    "max_lag_days": "Maximum lag days",
    "rainfall_peak_percentile": "Rainfall peak percentile",
    "auto_discharge_peak_prominence": "Auto discharge peak prominence",
    "minimum_discharge_peak_prominence": "Minimum discharge peak prominence",
    "minimum_distance_between_peaks": "Minimum distance between discharge peaks",
    "rolling_average_window": "Rolling average window (days)",
    "show_rolling_average": "Show rolling average on time series",
    "normalize_charts": "Normalize rainfall/discharge in selected charts",
    "plot_interaction_mode": "Plot interaction mode",
    "data_source": "Data source",
    "upload_csv": "Upload CSV",
    "load_sample_dataset": "Load sample dataset",
    "download_sample_csv": "Download sample CSV",
    "example_csv_format": "Example CSV format",
    "load_data_to_begin": "Load a CSV file or use the sample dataset to begin.",
    "data_preview": "Data Preview",
    "current_source": "Current source",
    "uploaded_csv": "Uploaded CSV",
    "sample_dataset": "Synthetic sample dataset",
    "rows": "Rows",
    "columns": "Columns",
    "missing_cells": "Missing cells",
    "date_parse_success": "Date parse success",
    "missing_value_report": "Missing value report",
    "date_range": "Date range",
    "preprocessing_check": "Preprocessing Check",
    "clean_rows": "Clean rows",
    "start_date": "Start date",
    "end_date": "End date",
    "remaining_missing": "Remaining missing",
    "run_analysis": "Run rainfall-discharge analysis",
    "analysis_completed": "Analysis completed.",
    "ready_to_analyze": "Set the data and analysis options, then press the analysis button.",
    "result_dashboard": "Result Dashboard",
    "total_rainfall": "Total rainfall",
    "mean_discharge": "Mean discharge",
    "max_discharge": "Max discharge",
    "min_discharge": "Min discharge",
    "estimated_lag": "Estimated lag",
    "best_correlation": "Best correlation",
    "rainfall_peaks": "Rainfall peaks",
    "discharge_peaks_short": "Discharge peaks",
    "tabs": ["Time Series", "Time Series Log Y", "Lag Analysis", "Scatter", "Distribution", "Peaks", "Report"],
    "rainfall_peak_events": "Rainfall peak events",
    "discharge_peak_events": "Discharge peak events",
    "hydrogeological_interpretation": "Hydrogeological Interpretation",
    "interpretation_caption": (
        "Interpretations are cautious exploratory statements, not definitive model conclusions."
    ),
    "report_preview": "Report preview",
}
