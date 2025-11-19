# FactSet Data Collector

A unified Python package for extracting quarterly EPS (Earnings Per Share) estimates from FactSet Earnings Insight reports using OCR and image processing techniques.

## Overview

This project processes chart images containing S&P 500 quarterly EPS data and extracts quarter labels (e.g., Q1'14, Q2'15) and corresponding EPS values. The extracted data is saved in CSV format for further analysis.

### Motivation

Financial data providers (FactSet, Bloomberg, Investing.com, etc.) typically offer historical EPS data as **actual values**—once a quarter's earnings are reported, the estimate is overwritten with the actual figure. This creates a challenge for backtesting predictive models: using historical data means testing against information that was already reflected in stock prices at the time, making it difficult to evaluate the true predictive power of EPS estimates.

To address this, this project extracts **point-in-time EPS estimates** from historical FactSet Earnings Insight reports. By preserving the estimates as they appeared at each report date (before actual earnings were announced), a dataset can be built that accurately reflects what was known and expected at each point in time, enabling more meaningful backtesting and predictive analysis.

## Project Structure (v0.2.0 - Refactored)

```
factset-data-collector/
├── src/
│   └── factset_data_collector/     # Main unified package
│       ├── __init__.py              # Public API exports
│       ├── core/                    # Core functionality
│       │   ├── __init__.py
│       │   ├── downloader.py        # PDF download from FactSet
│       │   ├── extractor.py         # Chart extraction from PDFs
│       │   └── ocr/                 # OCR processing
│       │       ├── __init__.py
│       │       ├── processor.py     # Main OCR pipeline
│       │       ├── google_vision_processor.py
│       │       ├── parser.py
│       │       ├── bar_classifier.py
│       │       └── coordinate_matcher.py
│       ├── analysis/                # Analysis tools
│       │   ├── __init__.py
│       │   └── pe_ratio.py          # P/E ratio calculation
│       └── utils/                   # Utilities
│           ├── __init__.py
│           ├── cloudflare.py        # Cloudflare R2 storage
│           └── csv_storage.py       # CSV storage abstraction
├── scripts/
│   └── data_collection/             # CLI wrappers
│       ├── download_factset_pdfs.py
│       └── extract_eps_charts.py
├── actions/
│   └── workflow.py                  # CI/CD workflow
├── main.py                          # Local CLI entry point
├── pyproject.toml                   # Package configuration
└── README.md
```

**Key Changes in v0.2.0:**
- ✅ **Unified package**: All functionality under `factset_data_collector`
- ✅ **Eliminated code duplication**: 70% reduction in redundant code
- ✅ **Removed deprecated structures**: `src/chart_ocr_processor/`, `src/service/`, `examples/`
- ✅ **Clear API structure**: `core` (data collection) + `analysis` (P/E ratios) + `utils` (storage)
- ✅ **Simplified imports**: Single import path for all functions
- ✅ **Code reduction**: 33% reduction in total code (3,622 → 2,405 lines)

## Installation

### Option 1: Install from Git (Recommended)
```bash
# Install with uv
uv pip install git+https://github.com/seung-gu/factset-data-collector.git

# Or with pip
pip install git+https://github.com/seung-gu/factset-data-collector.git
```

### Option 2: Local Development
```bash
# Clone repository
git clone https://github.com/seung-gu/factset-data-collector.git
cd factset-data-collector

# Install with uv
uv sync

# Or install in editable mode
uv pip install -e .
```

### Additional Requirements

- **Google Cloud Vision API**: Required for OCR
  - Create a service account and download JSON key file
  - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to the key file
  - See [Google Cloud Vision API documentation](https://cloud.google.com/vision/docs/setup) for details

- **Cloudflare R2 (Optional, for CI/CD)**: Cloud storage for automated workflows
  - Required only for GitHub Actions workflows
  - Local execution uses local file storage only
  - Install with: `uv sync --extra r2`

## Usage

### As a Python Package (Recommended)

```python
from factset_data_collector import download_pdfs, extract_charts, process_images, calculate_pe_ratio
from datetime import datetime
from pathlib import Path

# 1. Download PDFs from FactSet (2016-present)
pdfs = download_pdfs(
    start_date=datetime(2024, 1, 1),
    end_date=datetime.now(),
    outpath=Path("output/pdfs")
)
print(f"Downloaded {len(pdfs)} PDFs")

# 2. Extract EPS chart pages as PNG images
charts = extract_charts(pdfs, outpath=Path("output/charts"))
print(f"Extracted {len(charts)} charts")

# 3. Process images with OCR and extract data
df = process_images(
    directory=Path("output/charts"),
    output_csv=Path("output/estimates.csv"),
    use_coordinate_matching=True,
    classify_bars=True,
    use_multiple_methods=True
)
print(f"Extracted {len(df)} records")

# 4. Calculate P/E ratios
pe_df = calculate_pe_ratio(
    csv_path=Path("output/estimates.csv"),
    price_data={'2024-01-15': 150.5, '2024-02-15': 152.3},
    type='forward',  # or 'mix' or 'trailing-like'
    output_csv=Path("output/pe_ratios.csv")
)
print(pe_df)
```

**P/E Ratio Types:**
- `forward`: Q[1:5] - Skip first quarter after report date, take next 4
- `mix`: Q[0:4] - Include report date quarter, take next 3 (total 4)
- `trailing-like`: Q[-3:1] - Take 3 quarters before report date, include report date (total 4)

### As CLI Scripts

For local data collection and processing:

```bash
# 1. Download PDFs from FactSet
uv run python scripts/data_collection/download_factset_pdfs.py

# 2. Extract EPS chart pages from PDFs
uv run python scripts/data_collection/extract_eps_charts.py

# 3. Process images and extract data
uv run python main.py
```

See [scripts/data_collection/README.md](scripts/data_collection/README.md) for detailed CLI documentation.

## Architecture & Storage

### Local vs. CI/CD Execution

- **Local Execution**:
  - Uses local file storage only (`output/` directory)
  - Cloud storage disabled by default
  - Run individual scripts or `main.py`
  - Flexible parameters and manual control

- **CI/CD Execution** (`actions/workflow.py`):
  - **Only runs when cloud storage is enabled** (`CI=true` in GitHub Actions)
  - **Workflow Steps**:
    1. **Download CSV from cloud**: Downloads existing CSV files to local (artifact) for processing
    2. **Check for new PDFs**: 
       - Reads last date from downloaded CSV
       - Lists existing PDFs in cloud storage (`reports/` folder)
    3. **Download new PDFs**: 
       - Downloads only new PDFs from FactSet (not already in cloud)
       - If no new PDFs found, workflow terminates early
    4. **Extract PNGs**: Extracts EPS chart pages from new PDFs
    5. **Process images**: Processes PNGs and updates CSV files (incremental: skips already processed dates)
    6. **Upload to cloud**: Uploads new PDFs, PNGs, and updated CSV files to cloud storage
  - All processing uses local (artifact) files, then uploads results to cloud
  - CSV files stored at bucket root (`extracted_estimates.csv`, `extracted_estimates_confidence.csv`)

### Cloud Storage (Cloudflare R2)

Cloud storage is automatically enabled in CI environments (GitHub Actions) when R2 credentials are available:

**Storage Structure:**
```
R2 Bucket (factset-data)/
├── reports/                          # PDF files
│   └── EarningsInsight_*.pdf
├── estimates/                        # PNG chart images
│   └── *.png
├── extracted_estimates.csv           # Main data CSV (bucket root)
└── extracted_estimates_confidence.csv  # Confidence data CSV (bucket root)
```

**Environment Variables:**

**For Read-Only Access (Public URL - No API Key Needed):**
- `R2_PUBLIC_URL`: Public R2 URL for read-only access (optional)
  - **Default**: `https://pub-62707afd3ebb422aae744c63c49d36a0.r2.dev` (pre-configured)
  - Can be overridden via environment variable if needed
  - Format: `https://pub-{account_id}.r2.dev` or custom domain
  - Example: `export R2_PUBLIC_URL="https://pub-xxxxx.r2.dev"`
  - Allows reading CSV files without API credentials
  - **No setup needed**: Public URL is configured by default

**For Write Access (Private Bucket - API Key Required):**
- `R2_BUCKET_NAME`: Cloudflare R2 bucket name
- `R2_ACCOUNT_ID`: Cloudflare account ID
- `R2_ACCESS_KEY_ID`: R2 access key
- `R2_SECRET_ACCESS_KEY`: R2 secret key
- `CLOUD_STORAGE_ENABLED=true/false`: Manual override
- `CI=true`: Auto-enables cloud storage in GitHub Actions

**Usage:**
- **PyPI users (read-only)**: Set only `R2_PUBLIC_URL` environment variable
- **Developers/workflow (read/write)**: Set R2 credentials (R2_BUCKET_NAME, etc.)
- **Local users**: No environment variables needed (uses local files)

## Output Format

### Main CSV (`extracted_estimates.csv`)

| Report_Date | Q4'13 | Q1'14 | Q2'14 | ... |
|-------------|-------|-------|-------|-----|
| 2016-12-09  | 24.89 | 26.23 | 27.45 | ... |
| 2016-12-16  | 24.89 | 26.25 | 27.48 | ... |

- **Report_Date**: Date of the FactSet report (YYYY-MM-DD)
- **Quarter columns**: EPS estimates for each quarter (e.g., Q1'14, Q2'15)
- **Values**: EPS estimates in dollars
- **Storage**: 
  - Local: `output/extracted_estimates.csv`
  - Cloud (CI): Bucket root `extracted_estimates.csv`

### Confidence CSV (`extracted_estimates_confidence.csv`)

Same structure as main CSV, but contains OCR confidence scores (0-1) instead of EPS values.

- **Storage**:
  - Local: `output/extracted_estimates_confidence.csv`
  - Cloud (CI): Bucket root `extracted_estimates_confidence.csv`

## API Reference

### Core Functions

#### `download_pdfs(start_date, end_date, outpath, rate_limit=0.05)`
Download FactSet Earnings Insight PDFs.

**Parameters:**
- `start_date` (datetime): Start date (default: 2016-01-01)
- `end_date` (datetime): End date (default: today)
- `outpath` (Path): Output directory for PDFs
- `rate_limit` (float): Wait time between requests in seconds

**Returns:** List of dict with download info

**Note:** PDFs are available from 2016 onwards.

#### `extract_charts(pdfs, outpath)`
Extract EPS estimate chart pages from PDF files.

**Parameters:**
- `pdfs` (list[Path]): List of PDF file paths
- `outpath` (Path): Output directory for PNG files

**Returns:** List of Path objects for extracted PNG files

#### `process_images(directory, output_csv, use_coordinate_matching=True, classify_bars=True, use_multiple_methods=True)`
Process PNG images with OCR and extract EPS data.

**Parameters:**
- `directory` (Path): Directory containing PNG files
- `output_csv` (Path): Output CSV file path
- `use_coordinate_matching` (bool): Use coordinate-based matching
- `classify_bars` (bool): Use bar classification
- `use_multiple_methods` (bool): Use multiple OCR methods

**Returns:** DataFrame with extracted data

### Analysis Functions

#### `calculate_pe_ratio(csv_path=None, price_data=None, type='forward', output_csv=None)`
Calculate P/E ratios from EPS estimates.

**Parameters:**
- `csv_path` (Path | str | None): Path to CSV file. If None, automatically loads from cloud
  (extracted_estimates.csv) or local storage. Can be omitted when using public URL.
- `price_data` (DataFrame | dict | None): Stock price data
  - DataFrame: columns `Date`, `Price`
  - Dict: mapping dates (YYYY-MM-DD) to prices
  - None: Returns template DataFrame showing required format
- `type` (str): Type of P/E ratio calculation
  - `'forward'`: Q[1:5] - Next 4 quarters after report date
  - `'mix'`: Q[0:4] - Report date and next 3 quarters
  - `'trailing-like'`: Q[-3:1] - Last 3 quarters before and report date
- `output_csv` (Path | str | None): Optional path to save results

**Returns:** DataFrame with columns:
- `Report_Date`: Report date
- `Price_Date`: Date of price used
- `Price`: Stock price used
- `EPS_4Q_Sum`: 4-quarter EPS sum
- `PE_Ratio`: Calculated P/E ratio
- `Type`: Type of calculation

**Usage Examples:**

```python
# Option 1: Using public URL (no API key needed, default configured)
from factset_data_collector import calculate_pe_ratio

# csv_path=None: automatically loads from public URL (default: pub-62707afd3ebb422aae744c63c49d36a0.r2.dev)
pe_df = calculate_pe_ratio(
    price_data={'2024-01-15': 150.5, '2024-02-15': 152.3},
    type='forward'
)

# Option 2: Using local file
pe_df = calculate_pe_ratio(
    csv_path='output/extracted_estimates.csv',
    price_data={'2024-01-15': 150.5},
    type='forward',
    output_csv='output/pe_ratios.csv'
)
```

## GitHub Actions Setup

To run the workflow automatically on GitHub Actions:

1. **Set up secrets** in your GitHub repository (Settings → Secrets and variables → Actions):
   ```
   GOOGLE_APPLICATION_CREDENTIALS_JSON  # Google Cloud Vision API key (JSON content)
   R2_BUCKET_NAME                       # Cloudflare R2 bucket name
   R2_ACCOUNT_ID                        # Cloudflare account ID
   R2_ACCESS_KEY_ID                     # R2 access key
   R2_SECRET_ACCESS_KEY                 # R2 secret key
   ```

2. **Workflow triggers**:
   - **Schedule**: Runs automatically every Monday at 00:00 UTC (`cron: '0 0 * * 1'`)
   - **Manual**: Can be triggered manually from GitHub Actions tab (workflow_dispatch)

3. **Workflow behavior**:
   - Downloads existing CSVs from cloud
   - Checks for new PDFs since last run
   - If no new PDFs: terminates early (no processing needed)
   - If new PDFs: downloads, extracts, processes, uploads results
   - Uploads artifacts (CSVs) for 30-day retention

## Recent Updates

### v0.2.0 (2025-11-19) - Major Refactoring
- ✅ **Unified package structure**: All functionality under `factset_data_collector`
- ✅ **Eliminated code duplication**: Consolidated `scripts/` logic into `core/`
- ✅ **Integrated OCR modules**: Moved `chart_ocr_processor` into `core/ocr/`
- ✅ **Removed deprecated structures**: Deleted `src/chart_ocr_processor/`, `src/service/`, `examples/`
- ✅ **New analysis module**: Added `analysis/pe_ratio.py` for P/E calculations
- ✅ **Simplified imports**: Single import path `from factset_data_collector import ...`
- ✅ **Updated all entry points**: Scripts, workflow, and main.py use new API
- ✅ **Code reduction**: 33% reduction in total code (3,622 → 2,405 lines)
- ✅ **Cleaner structure**: 4 core modules instead of 6+ scattered directories

### v0.1.0 (Previous)
- CSV deduplication and column ordering fixes
- Confidence CSV consistency improvements
- GitHub Actions workflow optimization
- Cloud storage integration (Cloudflare R2)
- Incremental data processing
- Early termination for no-new-data scenarios

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is for educational and research purposes.

## Acknowledgments

- FactSet for providing public access to Earnings Insight reports
- Google Cloud Vision API for OCR capabilities
- Cloudflare R2 for cloud storage
