"""FactSet Report Analyzer - Unified API for collecting and analyzing EPS estimates from FactSet reports.

This package provides a comprehensive toolkit for:
- Downloading FactSet Earnings Insight PDFs
- Extracting EPS estimate charts from PDFs
- Processing charts with OCR to extract data
- Calculating P/E ratios from EPS estimates

Example:
    >>> from factset_report_analyzer import SP500, download_pdfs, extract_charts, process_images
    >>> from datetime import datetime
    >>> from pathlib import Path
    >>> 
    >>> # Download PDFs
    >>> pdfs = download_pdfs(
    ...     start_date=datetime(2024, 1, 1),
    ...     end_date=datetime.now(),
    ...     outpath=Path("output/pdfs")
    ... )
    >>> 
    >>> # Extract charts
    >>> charts = extract_charts(pdfs, outpath=Path("output/charts"))
    >>> 
    >>> # Process with OCR
    >>> df = process_images(
    ...     directory=Path("output/charts"),
    ...     output_csv=Path("output/estimates.csv")
    ... )
    >>> 
    >>> # Get P/E ratios using SP500 class
    >>> sp500 = SP500()
    >>> pe_df = sp500.pe_ratio  # forward (default)
    >>> sp500.set_type('trailing')
    >>> pe_trailing = sp500.pe_ratio
"""

from .core import download_pdfs, extract_charts, process_images, process_image
from .analysis import SP500
from .utils.plot import plot_pe_ratio_with_price

__version__ = "0.4.3"

__all__ = [
    'download_pdfs',
    'extract_charts',
    'process_images',
    'process_image',
    'SP500',
    'plot_pe_ratio_with_price',
]
