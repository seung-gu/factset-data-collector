# EPS Estimates Collector

A Python package for extracting quarterly EPS (Earnings Per Share) estimates from financial reports using OCR and image processing techniques.

> **⚠️ Disclaimer**: This package is for **educational and research purposes only**. For production use, please use [FactSet's official API](https://developer.factset.com/). This package processes publicly available PDF reports and is not affiliated with or endorsed by FactSet.

## Overview

This project processes chart images containing S&P 500 quarterly EPS data and extracts quarter labels (e.g., Q1'14, Q2'15) and corresponding EPS values. The extracted data is saved in CSV format for further analysis.

### Motivation

Financial data providers (FactSet, Bloomberg, Investing.com, etc.) typically offer historical EPS data as **actual values**—once a quarter's earnings are reported, the estimate is overwritten with the actual figure. This creates a challenge for backtesting predictive models: using historical data means testing against information that was already reflected in stock prices at the time, making it difficult to evaluate the true predictive power of EPS estimates.

To address this, this project extracts **point-in-time EPS estimates** from historical earnings insight reports. By preserving the estimates as they appeared at each report date (before actual earnings were announced), a dataset can be built that accurately reflects what was known and expected at each point in time, enabling more meaningful backtesting and predictive analysis.

## Installation

Install from PyPI:

```bash
pip install eps-estimates-collector
```

Or with `uv`:

```bash
uv pip install eps-estimates-collector
```

## Workflow Overview

The complete workflow from PDF documents to final P/E ratio calculation:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    📄 Step 1: PDF Download                          │
│                                                                     │
│  FactSet Earnings Insight Reports                                   │
│  └─> Download PDFs from FactSet website                             │
│      (e.g., EarningsInsight_20251114_111425.pdf)                    │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              🖼️  Step 2: EPS Chart Page Extraction                  │
│                                                                     │
│  PDF Document                                                       │
│  └─> Extract EPS chart page (Page 6)                                │
│      └─> Convert to PNG image                                       │
│          (e.g., 20161209-6.png)                                     │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              🔍 Step 3: OCR Processing & Data Extraction            │
│                                                                     │
│  Chart Image                                                        │
│  ├─> Google Cloud Vision API (149 text regions detected)            │
│  ├─> Coordinate-based matching (Q1'14 ↔ 27.85)                      │
│  ├─> Bar classification (dark = actual, light = estimate)           │
│  └─> Extract quarter labels and EPS values                          │
│                                                                     │
│  Output: CSV with quarterly EPS estimates                           │
│  └─> extracted_estimates.csv                                        │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│              📊 Step 4: P/E Ratio Calculation                       │
│                                                                     │
│  EPS Estimates + S&P 500 Prices                                     │
│  ├─> Load EPS data from public URL                                  │
│  ├─> Load S&P 500 prices from yfinance (2016-12-09 to today)        │
│  ├─> Calculate 4-quarter EPS sum (e.g. forward: Q(0)+Q(1)+Q(2)+Q(3))│
│  └─> Calculate P/E Ratio = Price / EPS_4Q_Sum                       │
│                                                                     │
│  Output: DataFrame with P/E ratios                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Visual Workflow

**Step 1: PDF Document** → Downloads FactSet Earnings Insight PDF reports

**Step 2: EPS Chart Page Extraction** → Extracts chart page from PDF and converts to PNG image

**Step 3: OCR Processing & Bar Classification** → Extracts quarter labels and EPS values, classifies bars (dark = actual, light = estimate)

**Step 4: P/E Ratio Calculation** → See example output below

## Usage

### Python API

```python
from eps_estimates_collector import fetch_sp500_pe_ratio

# Fetch P/E ratios (auto-loads CSV and S&P 500 prices)
pe_df = fetch_sp500_pe_ratio(type='forward')
print(pe_df)
```

**P/E Types:**
- `forward`: Q(0) + Q(1) + Q(2) + Q(3) - Report date quarter and next 3 quarters
- `trailing`: Q(-4) + Q(-3) + Q(-2) + Q(-1) - Last 4 quarters before report date

### Example: P/E Ratio Calculation Result

```python
from eps_estimates_collector import fetch_sp500_pe_ratio

# Fetch trailing P/E ratios
pe_df = fetch_sp500_pe_ratio(type='trailing')
print(pe_df)
```

**Output:**
```
📈 Loading S&P 500 price data from yfinance (2016-12-09 to 2025-11-20)...
✅ Loaded 2249 S&P 500 price points
     Report_Date  Price_Date        Price  EPS_4Q_Sum   PE_Ratio      Type
0     2016-12-09  2016-12-09  2259.530029      117.49  19.231680  trailing
1     2016-12-09  2016-12-12  2256.959961      117.49  19.209805  trailing
2     2016-12-09  2016-12-13  2271.719971      117.49  19.335433  trailing
3     2016-12-09  2016-12-14  2253.280029      117.49  19.178484  trailing
4     2016-12-09  2016-12-15  2262.030029      117.49  19.252958  trailing
...          ...         ...          ...         ...        ...       ...
2244  2025-11-07  2025-11-13  6737.490234      266.73  25.259589  trailing
2245  2025-11-14  2025-11-14  6734.109863      267.21  25.201564  trailing
2246  2025-11-14  2025-11-17  6672.410156      267.21  24.970660  trailing
2247  2025-11-14  2025-11-18  6617.319824      267.21  24.764492  trailing
2248  2025-11-14  2025-11-19  6642.160156      267.21  24.857454  trailing

[2249 rows x 6 columns]
```

### API Reference

#### `fetch_sp500_pe_ratio(type='forward')`

Fetch P/E ratios from EPS estimates using S&P 500 prices.

**Parameters:**
- `type` (str): `'forward'` or `'trailing'`
  - `'forward'`: Q(0) + Q(1) + Q(2) + Q(3) - Report date quarter and next 3 quarters
  - `'trailing'`: Q(-4) + Q(-3) + Q(-2) + Q(-1) - Last 4 quarters before report date

**Returns:** DataFrame with columns:
- `Report_Date`: EPS report date
- `Price_Date`: Trading day price date
- `Price`: S&P 500 closing price
- `EPS_4Q_Sum`: 4-quarter EPS sum
- `PE_Ratio`: Calculated P/E ratio
- `Type`: P/E type used

**Features:**
- ✅ No API keys required
- ✅ Always loads latest data from public URL
- ✅ No local files needed
- ✅ Auto-loads S&P 500 prices from yfinance

## Legal Disclaimer

**This package is provided for educational and research purposes only.**

- This package processes publicly available PDF reports from FactSet's website
- The data extraction and processing methods are implemented for academic research
- **This package is NOT affiliated with, endorsed by, or sponsored by FactSet**
- **For production use, please use [FactSet's official API](https://developer.factset.com/)**

**No Warranty**: This software is provided "as is" without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement.

**Limitation of Liability**: In no event shall the authors or copyright holders be liable for any claim, damages, or other liability arising from the use of this software.

**Data Usage**: Users are responsible for ensuring compliance with FactSet's terms of service and any applicable data usage agreements when using this package.

## License

MIT License

## Links

- **GitHub**: [seung-gu/eps-estimates-collector](https://github.com/seung-gu/eps-estimates-collector)
- **PyPI**: [eps-estimates-collector](https://pypi.org/project/eps-estimates-collector/)

