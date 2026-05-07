from __future__ import annotations

from pathlib import Path

from src.analysis import basic_statistics, build_analysis_summary
from src.data_loader import load_timeseries_csv
from src.preprocessing import clean_timeseries
from src.synthetic_data import generate_synthetic_karst_data, save_synthetic_data


PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample" / "synthetic_karst_timeseries.csv"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"


def main() -> None:
    """Generate synthetic data, run analyses, and save figures."""
    raw_df = generate_synthetic_karst_data(periods=365, seed=42)
    save_synthetic_data(raw_df, SAMPLE_DATA_PATH)

    df = clean_timeseries(load_timeseries_csv(SAMPLE_DATA_PATH))
    summary, lag_df, rainfall_events, discharge_peaks = build_analysis_summary(df, max_lag_days=14)

    figure_paths: list[Path] = []
    try:
        from src.visualization import create_all_figures

        figure_paths = create_all_figures(df, lag_df, FIGURES_DIR)
    except ModuleNotFoundError as exc:
        print(f"Figure generation skipped because a plotting dependency is missing: {exc.name}")
        print("Install dependencies with: pip install -r requirements.txt")

    print("\nKarst Rainfall-Response Analysis MVP")
    print("=" * 42)
    print(f"Synthetic data saved: {SAMPLE_DATA_PATH}")
    print(f"Record count: {len(df)} daily observations")
    print(f"Total rainfall: {summary.total_rainfall_mm:.1f} mm")
    print(f"Mean discharge: {summary.mean_discharge_m3s:.3f} m3/s")
    print(f"Maximum discharge: {summary.max_discharge_m3s:.3f} m3/s")
    print(f"Same-day rainfall-discharge correlation: {summary.rainfall_discharge_corr:.3f}")
    print(f"Estimated lag time: {summary.estimated_lag_days} days (corr={summary.estimated_lag_corr:.3f})")
    print(f"High rainfall events: {summary.rainfall_peak_count}")
    print(f"Discharge peaks: {summary.discharge_peak_count}")

    print("\nBasic statistics:")
    print(basic_statistics(df).to_string())

    print("\nTop rainfall events:")
    print(rainfall_events.sort_values("rainfall_mm", ascending=False).head(5).to_string(index=False))

    print("\nTop discharge peaks:")
    print(discharge_peaks.sort_values("spring_discharge_m3s", ascending=False).head(5).to_string(index=False))

    if figure_paths:
        print("\nFigures saved:")
        for path in figure_paths:
            print(f"- {path}")


if __name__ == "__main__":
    main()
