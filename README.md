# Karst Rainfall-Response Analysis

**Prepared by:** Arda Melih Cetin

A modular Python toolkit and Streamlit application for exploring, visualizing, and reporting spring discharge response to rainfall events in karst hydrogeology datasets.

> This project supports hydrogeological decision support and exploratory analysis. Synthetic data and correlation metrics should not be interpreted as definitive physical model results or proof of causality.

## Key Features

- **Data Ingestion & Preprocessing:** Upload CSV files or load a synthetic sample dataset, map custom column names, and handle missing values (`Linear interpolation`, `Forward fill`, `Drop missing rows`).
- **Core Hydrological Analysis:** Same-day correlation, lagged rainfall-discharge correlation, high rainfall event detection, and spring discharge peak detection.
- **Central Cosmetic Configuration (`config/plot_config.yaml`):** Every color, line width/style, marker shape/size, opacity, font family/size, figure dimension, DPI, grid, legend, and axis label for both static Matplotlib figures and interactive Streamlit charts lives in one YAML config file.
- **High-Performance Interactive Charts:** GPU-accelerated Plotly WebGL (`Scattergl`) with peak-preserving **LTTB downsampling**, WebGL rainfall stems, `@st.cache_data`, and lazy HTML/PNG exports for smooth 60 FPS zoom/pan on multi-decade daily series.
- **Live Cosmetic Sidebar:** Adjust colors, line/marker styles, typography, layout, and performance thresholds live in Streamlit and export/import your settings as YAML or JSON.
- **Google Colab Ready:** Clean `requirements-colab.txt` and one-click `notebooks/colab_runner.ipynb`.

## Project Structure

```text
Karst-Rainfall-Response-Analysis/
|-- app/
|   `-- streamlit_app.py         # Modular Streamlit UI + live cosmetic sidebar
|-- config/
|   `-- plot_config.yaml         # Central cosmetic & performance config
|-- data/
|   `-- sample/
|-- notebooks/
|   |-- 01_exploratory_analysis.ipynb
|   `-- colab_runner.ipynb       # One-click Google Colab runner
|-- packaging/
|   `-- windows/
|-- scripts/
|   `-- prepare_karst_input.py   # ERA5 + spring discharge CSV merger
|-- src/
|   |-- analysis.py              # Correlations, lag estimation, peak detection
|   |-- data_loader.py           # CSV I/O and column mapping
|   |-- downsampling.py          # Peak-preserving LTTB + WebGL stem builder
|   |-- interactive_charts.py    # WebGL Plotly figure builders (config-driven)
|   |-- plot_config.py           # YAML/JSON config loader & style mappers
|   |-- preprocessing.py         # Cleaning, filtering, normalization
|   |-- reporting.py             # Hydrogeological interpretation & MD/HTML reports
|   |-- synthetic_data.py        # Synthetic daily karst generator
|   |-- ui_config.py             # UI text strings
|   `-- visualization.py         # Static publication-quality Matplotlib figures
|-- main.py                      # CLI runner for static figures & summary
|-- requirements.txt             # Full local + Windows build dependencies
|-- requirements-colab.txt       # Lightweight dependencies for Google Colab / Linux
`-- README.md
```

## Installation

### Local (Windows / macOS / Linux)

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-colab.txt   # or requirements.txt for Windows packaging
```

### Google Colab

Open `notebooks/colab_runner.ipynb` in Google Colab, mount Drive or clone the repository, install `requirements-colab.txt`, customize `config/plot_config.yaml`, and generate static figures or launch Streamlit.

## Running the Project

### Command-Line Static Analysis & Figures

```bash
python main.py
```

Optional flags:

```bash
python main.py --input data/processed/my_spring.csv --config config/plot_config.yaml --max-lag 21 --formats png pdf
```

Figures are saved under `outputs/figures/` using the DPI, dimensions, colors, and typography defined in `config/plot_config.yaml`:
- `rainfall_discharge_timeseries.png`
- `rainfall_discharge_timeseries_log_y.png`
- `lag_correlation.png`
- `rainfall_discharge_scatter.png`
- `discharge_histogram.png`
- `peak_events.png`

### Interactive Streamlit App

```bash
streamlit run app/streamlit_app.py
```

## Expected CSV Format

```csv
date,rainfall_mm,mean_temperature_C,spring_discharge_m3s
2022-01-01,12.4,8.1,1.32
2022-01-02,0.0,7.5,1.41
```

## Preparing ERA5 and Discharge CSV Files

```bash
python scripts/prepare_karst_input.py \
  --era5 "path/to/ERA5_daily.csv" \
  --discharge "path/to/spring_discharge.csv" \
  --output "data/processed/karst_input.csv" \
  --join left
```
