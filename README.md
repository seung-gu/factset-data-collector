# FactSet Data Collector

A Python application for extracting quarterly EPS (Earnings Per Share) estimates from FactSet Earnings Insight reports using OCR and image processing techniques.

## Overview

This project processes chart images containing S&P 500 quarterly EPS data and extracts quarter labels (e.g., Q1'14, Q2'15) and corresponding EPS values. The extracted data is saved in CSV format for further analysis.

### Motivation

Financial data providers (FactSet, Bloomberg, Investing.com, etc.) typically offer historical EPS data as **actual values**—once a quarter's earnings are reported, the estimate is overwritten with the actual figure. This creates a challenge for backtesting predictive models: using historical data means testing against information that was already reflected in stock prices at the time, making it difficult to evaluate the true predictive power of EPS estimates.

To address this, this project extracts **point-in-time EPS estimates** from historical FactSet Earnings Insight reports. By preserving the estimates as they appeared at each report date (before actual earnings were announced), a dataset can be built that accurately reflects what was known and expected at each point in time, enabling more meaningful backtesting and predictive analysis.

## Project Structure

```
factset-data-collector/
├── src/
│   ├── chart_ocr_processor/      # Image processing and OCR
│   │   ├── __init__.py
│   │   ├── bar_classifier.py      # Bar graph classification
│   │   ├── coordinate_matcher.py  # Coordinate-based matching
│   │   ├── google_vision_processor.py  # Google Cloud Vision OCR
│   │   ├── parser.py              # Quarter and EPS parsing logic
│   │   └── processor.py           # Main processing pipeline (local only)
│   └── service/                   # Cloud storage and utilities
│       ├── cloudflare.py          # Cloudflare R2 storage integration
│       └── csv_storage.py         # CSV storage abstraction (cloud/local)
├── actions/
│   └── workflow.py                # Complete automated workflow (CI/CD)
├── scripts/
│   ├── data_collection/          # Data collection scripts
│   │   ├── download_factset_pdfs.py  # Download PDFs from FactSet
│   │   └── extract_eps_charts.py    # Extract charts from PDFs
│   ├── testing/                   # Test scripts
│   └── visualization/            # Visualization scripts
├── output/                        # Local output directory
│   ├── estimates/                 # Extracted PNG images
│   ├── factset_pdfs/              # Downloaded PDF files
│   ├── extracted_estimates.csv    # Main data CSV
│   └── extracted_estimates_confidence.csv  # Confidence data CSV
├── main.py                         # Main entry point (image processing only, local)
└── pyproject.toml                  # Project configuration
```

## Installation

This project uses `uv` for dependency management:

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync
```

### Additional Requirements

- **Google Cloud Vision API**: Requires authentication
  - Create a service account and download JSON key file
  - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to the key file
  - See [Google Cloud Vision API documentation](https://cloud.google.com/vision/docs/setup) for details

- **Cloudflare R2 (Optional, for CI/CD)**: Cloud storage for automated workflows
  - Required only for GitHub Actions workflows
  - Local execution uses local file storage only
  - Install with: `uv sync --extra r2`

## Usage

### Data Collection

Before processing images, you need to collect the data from FactSet. The data collection process consists of two steps:

#### Step 1: Download PDFs from FactSet

The script downloads Earnings Insight PDFs from FactSet's public repository by reverse-searching from today back to 2000.

```bash
uv run python scripts/data_collection/download_factset_pdfs.py
```

**How it works**:
- Searches FactSet's public URL: `https://advantage.factset.com/hubfs/Website/Resources%20Section/Research%20Desk/Earnings%20Insight/`
- Tries multiple date formats (MMDDYY, MMDDYYYY) for each date
- Downloads PDFs in reverse chronological order (newest first)
- Saves PDFs to `output/factset_pdfs/` directory (local)
- In CI environments: Also uploads to Cloudflare R2 at `reports/` path
- Creates an index file `output/factset_pdfs_index.json` with download metadata
- Includes rate limiting (0.05 seconds between requests) to be respectful
- **Incremental updates**: If CSV exists, only downloads PDFs after the last processed date

**Example output**:
```
🔍 FactSet Earnings Insight PDF reverse search and download
Period: 2025-11-17 → 2000-01-01 (reverse)
================================================================================
✅ 2025-11-17: 111725      |  523.7 KB | Download complete
✅ 2025-11-10: 111025      |  987.6 KB | Download complete
...
📊 Final Results
URLs tested: 9,500
PDFs found: 385
Total size: 1250.3 MB
```

#### Step 2: Extract EPS Chart Pages from PDFs

The script extracts the specific page containing the "Bottom-Up EPS Estimates" chart from each PDF and converts it to a high-resolution PNG image.

```bash
uv run python scripts/data_collection/extract_eps_charts.py
```

**How it works**:
- Opens each PDF file in `output/factset_pdfs/`
- Searches for pages containing keywords:
  - "Bottom-Up EPS Estimates: Current & Historical"
  - "Bottom-up EPS Estimates: Current & Historical"
  - "Bottom-Up EPS: Current & Historical"
- If keyword is found at the bottom of a page, extracts the next page (chart is typically on the following page)
- Converts the target page to PNG at 300 DPI resolution
- Saves PNG files to `output/estimates/` with naming format: `YYYYMMDD.png` (local)
- In CI environments: Also uploads to Cloudflare R2 at `estimates/` path
- **Incremental updates**: Skips PNGs that already exist locally or in cloud
- **Date filtering**: If CSV exists, only processes PDFs after the last processed date

**Example output**:
```
🔍 Extracting EPS charts from FactSet PDFs
Target: 385 PDFs all
================================================================================
✅ 2016-12-09  Page  20 -> output/estimates/20161209.png
✅ 2016-12-16  Page  20 -> output/estimates/20161216.png
✅ 2016-12-23  Page  20 -> output/estimates/20161223.png
...
📊 Result: 379 files extracted
```

**Example extracted chart image**:

<img src="output/preprocessing_test/20161209.png" alt="Extracted EPS Chart" width="600">

The extracted PNG images contain the quarterly EPS chart with:
- Quarter labels (Q1'14, Q2'14, etc.) at the bottom
- EPS values (actuals and estimates) as bar graphs
- Dark bars = Actual values
- Light bars = Estimated values (marked with `*` in output)

### Basic Usage

#### Option 1: Image Processing Only (main.py)

Process already extracted PNG images:

```bash
# Process all images in output/estimates directory
uv run python main.py

# Specify custom input/output paths
uv run python main.py --input-dir output/estimates --output output/results.csv

# Process only first 5 images (for testing)
uv run python main.py --limit 5
```

**Command Line Options:**
- `--input-dir`: Directory containing PNG images (default: `output/estimates`)
- `--output`: Output CSV file path (default: `output/extracted_estimates.csv`)
- `--limit`: Maximum number of images to process (for testing)
- `--no-coordinate-matching`: Disable coordinate-based matching
- `--no-bar-classification`: Disable bar graph classification
- `--single-method`: Use single method only (instead of ensemble)

#### Option 2: Complete Workflow (actions/workflow.py)

Run the complete automated pipeline for CI/CD environments:

```bash
# Run complete workflow (CI environment only)
uv run python actions/workflow.py
```

**Execution Modes:**

- **Local Execution** (`main.py`):
  - Uses local file storage only (`output/` directory)
  - Cloud storage is **disabled** (even if R2 credentials are provided)
  - Suitable for development and testing
  - Requires PDFs and PNGs to be downloaded/extracted first
  - Use individual scripts (`download_factset_pdfs.py`, `extract_eps_charts.py`) for data collection

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

See [scripts/data_collection/README.md](scripts/data_collection/README.md) for detailed workflow documentation.

#### GitHub Actions Setup

To run the workflow automatically on GitHub Actions:

1. **Create GitHub Secrets** (Settings → Secrets and variables → Actions):
   - `GOOGLE_APPLICATION_CREDENTIALS_JSON`: Google Cloud service account JSON key file content
   - `R2_BUCKET_NAME`: Cloudflare R2 bucket name (e.g., `factset-data`)
   - `R2_ACCOUNT_ID`: Cloudflare R2 account ID
   - `R2_ACCESS_KEY_ID`: Cloudflare R2 access key ID
   - `R2_SECRET_ACCESS_KEY`: Cloudflare R2 secret access key

2. **Workflow file**: `.github/workflows/data-collection.yml` is already configured
   - Runs weekly on Monday at 00:00 UTC (09:00 KST)
   - Can also be triggered manually via "Run workflow" button

3. **Workflow execution** (automated pipeline):
   - **Step 0**: Downloads existing CSV files from cloud to local (artifact)
   - **Step 1**: Checks for new PDFs by comparing cloud storage with FactSet
   - **Step 2**: Downloads new PDFs from FactSet (only if new ones exist, otherwise terminates)
   - **Step 3**: Extracts EPS chart pages as PNGs from new PDFs
   - **Step 4**: Processes images and updates CSV files (incremental: skips already processed dates)
   - **Step 5**: Uploads new files to Cloudflare R2:
     - New PDFs → `reports/` folder in R2 bucket
     - New PNGs → `estimates/` folder in R2 bucket
     - Updated CSV files → Bucket root
   - Saves CSV results as GitHub Actions artifacts (30-day retention)

4. **Cloud Storage Structure** (R2 Bucket):
   ```
   factset-data (bucket)
   ├── extracted_estimates.csv
   ├── extracted_estimates_confidence.csv
   ├── estimates/
   │   └── YYYYMMDD.png
   └── reports/
       └── EarningsInsight_YYYYMMDD_*.pdf
   ```

## Output Format

The extracted data is saved as **two separate CSV files**:

### Main Data (`extracted_estimates.csv`)

Wide format with the following structure:
- `Report_Date`: Date extracted from filename (YYYY-MM-DD format)
- Quarter columns: `Q1'14`, `Q2'14`, `Q3'14`, etc. (sorted chronologically)
- Estimated values are marked with `*` suffix

Example:
```csv
Report_Date,Q1'14,Q2'14,Q3'14,Q4'14,Q1'15,...,Q1'17,Q2'17
2016-12-09,27.85,29.67,29.96,30.33,28.43,...,30.61*,32.64*
```

### Confidence Data (`extracted_estimates_confidence.csv`)

Separate file containing confidence scores:
- `Report_Date`: Date extracted from filename
- `Confidence`: Overall confidence score (0-100%) combining bar classification confidence and consistency with previous week's data

Example:
```csv
Report_Date,Confidence
2016-12-09,100.0
```

**Storage Locations:**
- **Local**: `output/extracted_estimates.csv`, `output/extracted_estimates_confidence.csv`
- **Cloud (CI)**: Bucket root (`extracted_estimates.csv`, `extracted_estimates_confidence.csv`)

**Visualization of extraction result**:

<img src="output/preprocessing_test/20161209-6_bar_classification.png" alt="Final Extraction Result" width="600">

The visualization shows:
- **Red bounding boxes**: Quarter labels (Q1'14, Q2'14, etc.) matched with actual EPS values (dark bars)
- **Magenta bounding boxes**: Quarter labels matched with estimated EPS values (light bars)
- All quarter-value pairs are correctly matched using coordinate-based spatial relationships

The confidence score is calculated as:
- 50% weight: Bar graph classification consistency (3/3 methods agree = 100%, 2/3 = 67%, 1/3 = 33%)
- 50% weight: Consistency with closest previous week's actual data (80% match threshold)

## Image Preprocessing Pipeline

The image preprocessing pipeline is designed to classify bar graphs as either **actual values** (dark bars) or **estimated values** (light bars). This classification is essential for correctly marking estimates with `*` in the output CSV.

### Three-Method Ensemble Classification

After testing 14 different preprocessing techniques, **three methods** were selected that work together in an ensemble approach:

1. **Adaptive Threshold** (Threshold: 0.7):
   - Creates sharp boundaries between bars and background
   - Optimal for fully filled bar graphs with clear contours
   - Classification: white pixel ratio > 0.7 = dark bar

2. **Morphology Closing** (Threshold: 0.5, **inverted logic**):
   - Fills gaps and holes in partially filled bars
   - Optimal for partially filled bar graphs
   - **Important**: Uses inverted logic due to hole-filling nature
   - Classification: white pixel ratio > 0.5 = light bar (inverted)

3. **OTSU Binary Inverted** (Threshold: 0.7):
   - Inverted binary image (dark regions become white)
   - Helps identify dark bars more clearly
   - Classification: white pixel ratio > 0.7 = dark bar

### Classification Process

1. **Preprocessing**: Convert image to grayscale and generate three preprocessed versions
2. **Bar Region Extraction**: Crop the bar region between each quarter label and its corresponding EPS value
3. **Voting**: Each method votes 'dark' or 'light' for each bar
4. **Confidence Scoring**:
   - **High (3/3)**: All three methods agree → 100% confidence
   - **Medium (2/3)**: Two methods agree → 67% confidence
   - **Low (1/3 or 0/3)**: Methods disagree → 33% confidence
5. **Final Classification**: Majority vote determines if bar is dark (actual) or light (estimate)

### Key Design Decisions

- **Ensemble approach**: Single method may misclassify, but three methods together provide robust classification
- **Method-specific logic**: Morphology Closing requires inverted logic because it fills holes (low ratio = dark, high ratio = light)
- **Threshold tuning**: Optimal thresholds (0.5-0.7) were determined through distribution analysis of white pixel ratios
- **Perfect agreement achievable**: With proper thresholds and logic, all three methods achieve 100% agreement on test images

This preprocessing pipeline ensures accurate distinction between actual and estimated EPS values, which is critical for data quality.

## Architecture & Storage

### Local vs CI/CD Execution

**Local Execution:**
- All files stored in `output/` directory
- Cloud storage explicitly disabled
- Use `main.py` for image processing only
- Use individual scripts (`download_factset_pdfs.py`, `extract_eps_charts.py`) for data collection

**CI/CD Execution (GitHub Actions):**
- Cloud storage automatically enabled when `CI=true`
- Use `actions/workflow.py` for complete automated pipeline
- **Workflow Process**:
  1. Downloads CSV files from cloud to local (artifact) for processing
  2. Checks cloud storage for existing PDFs to avoid duplicates
  3. Downloads only new PDFs from FactSet (terminates if none found)
  4. Processes new PDFs → PNGs → CSV locally (all in artifact)
  5. Uploads new files back to cloud storage
- All processing happens locally (artifact), then results uploaded to cloud
- Incremental updates: Only processes new data based on existing CSV

### Cloud Storage Integration

- **Provider**: Cloudflare R2 (S3-compatible)
- **Storage Abstraction**: `src/service/csv_storage.py` handles cloud/local switching
- **File Upload**: `src/service/cloudflare.py` provides upload/download functions
- **Automatic Detection**: Cloud storage enabled only in CI environments or when explicitly enabled

## Development History

For detailed development history, see [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md).

**Brief Summary**: Started with cloud APIs (OpenAI, Gemini) → Local Tesseract OCR → CRAFT model → **Final: Google Cloud Vision API** with coordinate-based matching and three-method ensemble bar graph classification.

**Recent Updates**:
- Added Cloudflare R2 cloud storage integration for CI/CD workflows
- Separated confidence data into separate CSV file (`extracted_estimates_confidence.csv`)
- Implemented incremental update logic (skip already processed data)
- Created automated workflow (`actions/workflow.py`) for CI/CD environments
- Added storage abstraction layer (`src/service/`) for hybrid cloud/local execution
- Removed `R2_BASE_PATH` configuration (files stored at bucket root and folders)



## Contributing


