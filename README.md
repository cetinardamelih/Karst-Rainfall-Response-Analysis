# Karst Rainfall-Response Analysis

**Prepared by:** Arda Melih Cetin

This Python-based MVP project is designed to explore, visualize, and report spring discharge response after rainfall events in karst hydrogeology datasets.

This project is not a full physical hydrogeological model. Synthetic data generation and correlation analyses are included to test the workflow and provide a starting point for using real ERA5 rainfall data and spring discharge CSV files. Results should not be interpreted as proof of causality or as definitive field-scale karst system parameters.

## Features

- Upload CSV files or use a built-in synthetic sample dataset
- Map different input column names to the application's standard schema
- Handle missing values with linear interpolation, forward fill, or row removal
- Clean rainfall, temperature, and spring discharge time series
- Calculate same-day rainfall-discharge correlation
- Estimate rainfall-response lag using lagged correlation analysis
- Detect high rainfall events and discharge peaks
- Generate interactive Plotly charts
- Download cleaned data, lag results, summary metrics, and reports
- Convert ERA5 and spring discharge CSV files into the application input format

## Project Structure

```text
karst-rainfall-response-analysis/
|-- app/
|   `-- streamlit_app.py
|-- data/
|   |-- raw/
|   |-- processed/
|   `-- sample/
|-- notebooks/
|-- outputs/
|   |-- figures/
|   `-- reports/
|-- packaging/
|-- scripts/
|   `-- prepare_karst_input.py
|-- src/
|   |-- analysis.py
|   |-- data_loader.py
|   |-- preprocessing.py
|   |-- synthetic_data.py
|   `-- visualization.py
|-- main.py
|-- requirements.txt
`-- README.md
```

## Installation

Windows PowerShell:

```powershell
cd "karst-rainfall-response-analysis"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

macOS/Linux:

```bash
cd karst-rainfall-response-analysis
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the App

Start the Streamlit interface:

```powershell
streamlit run app\streamlit_app.py
```

The browser usually opens at:

```text
http://localhost:8501
```

Run the command-line sample analysis:

```powershell
python main.py
```

This command generates synthetic daily data, runs the core analyses, and saves figures under `outputs/figures/`.

## Expected CSV Format

The application expects one CSV file with these columns:

```csv
date,rainfall_mm,mean_temperature_C,spring_discharge_m3s
2022-01-01,12.4,8.1,1.32
2022-01-02,0.0,7.5,1.41
```

Column meanings:

| Column | Description |
| --- | --- |
| `date` | Daily date |
| `rainfall_mm` | Daily total rainfall in mm/day |
| `mean_temperature_C` | Daily mean air temperature in degrees Celsius |
| `spring_discharge_m3s` | Spring discharge in m3/s |

## Preparing ERA5 and Discharge CSV Files

If the ERA5 file contains `time`, `precipitation_mm`, and `tmean_C`, and the discharge file contains metadata rows followed by a `Date;Discharge (L/s)` table, use:

```powershell
python scripts\prepare_karst_input.py --era5 "path\to\Schwarzbach_daily_2003_2022_MERGED.csv" --discharge "path\to\ALP_40_AT@Ursprungquelle.csv" --output "data\processed\ALP_40_AT_Ursprungquelle_karst_input.csv" --join left
```

The script:

- Skips metadata rows in the discharge file
- Parses the `Date` column
- Converts `Discharge (L/s)` to numeric values
- Removes non-numeric discharge annotation rows
- Converts discharge from L/s to m3/s
- Merges ERA5 and discharge data by `date`
- Writes a single CSV file that the app can read

The output file contains:

```text
date,rainfall_mm,mean_temperature_C,spring_discharge_m3s
```

If your column names differ, pass them explicitly:

```powershell
--era5-date-column "time"
--rainfall-column "precipitation_mm"
--temperature-column "tmean_C"
--discharge-date-column "Date"
--discharge-column "Discharge (L/s)"
```

If discharge dates use month-first formatting, for example `01/31/2003`, add:

```powershell
--discharge-month-first
```

## Hydrogeological Meaning

- Total rainfall summarizes water input during the selected period.
- Mean and maximum discharge provide a first view of general spring flow conditions and peak response.
- Same-day rainfall-discharge correlation shows the linear relationship between rainfall and discharge on the same day.
- Lag correlation estimates how many days after rainfall the spring discharge response is strongest.
- Rainfall events and discharge peaks identify candidate recharge-response periods.
- Rolling average charts smooth short-term discharge variability and make broader trends easier to inspect.

These analyses are exploratory. Field interpretation should also consider geology, aquifer geometry, measurement uncertainty, evapotranspiration, snowmelt, water abstraction, and data quality.

## Outputs

The Streamlit interface can export:

- Cleaned data CSV
- Lag correlation results CSV
- Summary metrics CSV
- Summary metrics JSON
- Markdown report
- HTML report
- Chart outputs as HTML or PNG

The command-line analysis saves these figures under `outputs/figures/`:

- `rainfall_discharge_timeseries.png`
- `lag_correlation.png`
- `rainfall_discharge_scatter.png`
- `discharge_histogram.png`

## Windows Desktop App

Windows PyInstaller launcher and Inno Setup installer files are stored under `packaging/windows/`. To build the installer:

```bat
pip install -r requirements.txt
packaging\windows\build_windows.bat
```

Then compile `packaging/windows/installer.iss` with Inno Setup to create `setup.exe`. See `packaging/windows/README_WINDOWS.md` for details.

## Note

This tool is intended for hydrogeological decision support, exploratory analysis, and visualization. It does not produce definitive model results by itself.
