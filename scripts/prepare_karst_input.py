from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


OUTPUT_COLUMNS = [
    "date",
    "rainfall_mm",
    "mean_temperature_C",
    "spring_discharge_m3s",
]


def find_discharge_header(path: Path, date_column: str, discharge_column: str) -> int:
    """Return the zero-based row number where the discharge CSV table starts."""
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for row_number, line in enumerate(handle):
            parts = [part.strip() for part in line.strip().split(";")]
            if date_column in parts and discharge_column in parts:
                return row_number

    raise ValueError(
        f"Could not find a discharge table header containing {date_column!r} "
        f"and {discharge_column!r} in {path}."
    )


def load_discharge_csv(
    path: Path,
    date_column: str,
    discharge_column: str,
    dayfirst: bool,
) -> pd.DataFrame:
    """Load spring discharge data and convert liters/second to cubic meters/second."""
    header_row = find_discharge_header(path, date_column, discharge_column)
    df = pd.read_csv(
        path,
        sep=";",
        skiprows=header_row,
        encoding="utf-8-sig",
        encoding_errors="replace",
    )

    discharge_lps = pd.to_numeric(df[discharge_column], errors="coerce")
    cleaned = pd.DataFrame(
        {
            "date": pd.to_datetime(df[date_column], errors="coerce", dayfirst=dayfirst),
            "spring_discharge_m3s": discharge_lps / 1000.0,
        }
    )

    before = len(cleaned)
    cleaned = cleaned.dropna(subset=["date", "spring_discharge_m3s"])
    dropped = before - len(cleaned)

    duplicate_count = int(cleaned.duplicated(subset=["date"]).sum())
    cleaned = (
        cleaned.sort_values("date")
        .groupby("date", as_index=False)
        .mean(numeric_only=True)
    )

    print(f"Discharge rows read: {before}")
    print(f"Discharge rows dropped because date/discharge was not numeric: {dropped}")
    print(f"Duplicate numeric discharge dates averaged: {duplicate_count}")
    return cleaned


def load_era5_csv(
    path: Path,
    date_column: str,
    rainfall_column: str,
    temperature_column: str,
) -> pd.DataFrame:
    """Load ERA5 daily rainfall and temperature columns."""
    df = pd.read_csv(path)
    cleaned = pd.DataFrame(
        {
            "date": pd.to_datetime(df[date_column], errors="coerce"),
            "rainfall_mm": pd.to_numeric(df[rainfall_column], errors="coerce"),
            "mean_temperature_C": pd.to_numeric(df[temperature_column], errors="coerce"),
        }
    )

    before = len(cleaned)
    cleaned = cleaned.dropna(subset=["date"])
    cleaned = cleaned.sort_values("date").drop_duplicates(subset=["date"], keep="first")
    cleaned.loc[cleaned["rainfall_mm"] < 1.0, "rainfall_mm"] = 0.0
    dropped = before - len(cleaned)

    print(f"ERA5 rows read: {before}")
    print(f"ERA5 rows dropped because date was invalid or duplicated: {dropped}")
    return cleaned


def prepare_input(
    era5_path: Path,
    discharge_path: Path,
    output_path: Path,
    join: str,
    fill_missing: bool,
    era5_date_column: str,
    rainfall_column: str,
    temperature_column: str,
    discharge_date_column: str,
    discharge_column: str,
    discharge_dayfirst: bool,
) -> pd.DataFrame:
    era5 = load_era5_csv(
        era5_path,
        date_column=era5_date_column,
        rainfall_column=rainfall_column,
        temperature_column=temperature_column,
    )
    discharge = load_discharge_csv(
        discharge_path,
        date_column=discharge_date_column,
        discharge_column=discharge_column,
        dayfirst=discharge_dayfirst,
    )

    merged = era5.merge(discharge, on="date", how=join)
    merged = merged.sort_values("date").reset_index(drop=True)

    if fill_missing:
        numeric_columns = ["rainfall_mm", "mean_temperature_C", "spring_discharge_m3s"]
        merged[numeric_columns] = merged[numeric_columns].interpolate(limit_direction="both")

    merged = merged[OUTPUT_COLUMNS]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)

    print(f"Merged rows written: {len(merged)}")
    print(f"Date range: {merged['date'].min().date()} to {merged['date'].max().date()}")
    print("Remaining missing values:")
    print(merged.isna().sum().to_string())
    print(f"Output CSV: {output_path}")

    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge an ERA5 daily CSV and a spring discharge CSV into the "
            "Karst Rainfall-Response Analysis input format."
        )
    )
    parser.add_argument("--era5", required=True, type=Path, help="Path to the ERA5 daily CSV.")
    parser.add_argument("--discharge", required=True, type=Path, help="Path to the spring discharge CSV.")
    parser.add_argument("--output", required=True, type=Path, help="Output CSV path.")
    parser.add_argument(
        "--join",
        choices=["inner", "left"],
        default="inner",
        help="Use inner for dates present in both files, or left to keep all ERA5 dates.",
    )
    parser.add_argument(
        "--fill-missing",
        action="store_true",
        help="Interpolate remaining numeric missing values in the merged file.",
    )
    parser.add_argument("--era5-date-column", default="time")
    parser.add_argument("--rainfall-column", default="precipitation_mm")
    parser.add_argument("--temperature-column", default="tmean_C")
    parser.add_argument("--discharge-date-column", default="Date")
    parser.add_argument("--discharge-column", default="Discharge (L/s)")
    parser.add_argument(
        "--discharge-month-first",
        action="store_true",
        help="Use this only if the discharge dates are month/day/year instead of day/month/year.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_input(
        era5_path=args.era5,
        discharge_path=args.discharge,
        output_path=args.output,
        join=args.join,
        fill_missing=args.fill_missing,
        era5_date_column=args.era5_date_column,
        rainfall_column=args.rainfall_column,
        temperature_column=args.temperature_column,
        discharge_date_column=args.discharge_date_column,
        discharge_column=args.discharge_column,
        discharge_dayfirst=not args.discharge_month_first,
    )


if __name__ == "__main__":
    main()
