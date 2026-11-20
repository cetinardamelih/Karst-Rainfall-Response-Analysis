from __future__ import annotations

import argparse
from pathlib import Path

from src.analysis import basic_statistics, build_analysis_summary
from src.data_loader import load_timeseries_csv
from src.plot_config import DEFAULT_CONFIG_PATH, load_plot_config
from src.preprocessing import clean_timeseries
from src.synthetic_data import generate_synthetic_karst_data, save_synthetic_data


PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample" / "synthetic_karst_timeseries.csv"
FIGURES_DIR = PROJECT_ROOT / "outputs" / "figures"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Karst Rainfall-Response Analysis and generate static publication figures."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Optional CSV path. If omitted, generates and uses the synthetic sample dataset.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to central plot cosmetic YAML/JSON config.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=FIGURES_DIR,
        help="Directory where static figures are saved.",
    )
    parser.add_argument("--max-lag", type=int, default=14, help="Maximum lag in days.")
    parser.add_argument("--periods", type=int, default=365, help="Synthetic dataset length in days.")
    parser.add_argument(
        "--formats",
        nargs="+",
        default=None,
        help="Override static save formats from config (e.g. --formats png pdf).",
    )
    return parser.parse_args()


def main() -> None:
    """Load or generate karst data, run analyses, and save Matplotlib figures."""
    args = parse_args()
    plot_config = load_plot_config(args.config)
    if args.formats:
        plot_config["layout"]["save_formats"] = args.formats

    if args.input is not None:
        data_path = args.input
    else:
        raw_df = generate_synthetic_karst_data(periods=args.periods, seed=42)
        data_path = save_synthetic_data(raw_df, SAMPLE_DATA_PATH)

    df = clean_timeseries(load_timeseries_csv(data_path))
    summary, lag_df, rainfall_events, discharge_peaks = build_analysis_summary(df, max_lag_days=args.max_lag)

    figure_paths: list[Path] = []
    try:
        from src.visualization import create_all_figures

        figure_paths = create_all_figures(
            df,
            lag_df,
            args.output_dir,
            config=plot_config,
            rainfall_events=rainfall_events,
            discharge_peaks=discharge_peaks,
        )
    except ModuleNotFoundError as exc:
        print(f"Figure generation skipped because a plotting dependency is missing: {exc.name}")
        print("Install dependencies with: pip install -r requirements.txt")

    print("\nKarst Rainfall-Response Analysis")
    print("=" * 42)
    print(f"Dataset: {data_path}")
    print(f"Plot config: {args.config}")
    print(f"Record count: {len(df)} daily observations")
    print(f"Total rainfall: {summary.total_rainfall_mm:.1f} mm")
    print(f"Mean discharge: {summary.mean_discharge_m3s:.3f} m3/s")
    print(f"Maximum discharge: {summary.max_discharge_m3s:.3f} m3/s")
    print(f"Minimum discharge: {summary.min_discharge_m3s:.3f} m3/s")
    print(f"Same-day rainfall-discharge correlation: {summary.rainfall_discharge_corr:.3f}")
    print(f"Estimated lag time: {summary.estimated_lag_days} days (corr={summary.estimated_lag_corr:.3f})")
    print(f"High rainfall events: {summary.rainfall_peak_count}")
    print(f"Discharge peaks: {summary.discharge_peak_count}")

    print("\nBasic statistics:")
    print(basic_statistics(df).to_string())

    if not rainfall_events.empty:
        print("\nTop rainfall events:")
        print(rainfall_events.sort_values("rainfall_mm", ascending=False).head(5).to_string(index=False))

    if not discharge_peaks.empty:
        print("\nTop discharge peaks:")
        print(discharge_peaks.sort_values("spring_discharge_m3s", ascending=False).head(5).to_string(index=False))

    if figure_paths:
        print("\nFigures saved:")
        for path in figure_paths:
            print(f"- {path}")


if __name__ == "__main__":
    main()
