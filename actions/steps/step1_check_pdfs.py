"""Step 1: Check for new PDFs by comparing CSV and cloud storage."""

from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

from src.eps_estimates_collector.utils import list_cloud_files
from src.eps_estimates_collector.utils.cloudflare import read_csv_from_cloud


def check_for_new_pdfs() -> tuple[datetime, set[str]]:
    """
    Check for new PDFs by comparing CSV data and cloud storage.
    
    Returns:
        Tuple of (download_start_date, cloud_pdf_names)
        - download_start_date: Date to start downloading from
        - cloud_pdf_names: Set of PDF filenames already in cloud
    """
    print("-" * 80)
    print(" 🔍 Step 1: Checking for new PDFs...")
    
    # Get last date from public URL CSV
    last_date = None
    try:
        df = read_csv_from_cloud("extracted_estimates.csv")
        
        if df is not None and not df.empty and 'Report_Date' in df.columns:
            df['Report_Date'] = pd.to_datetime(df['Report_Date'])
            last_date = df['Report_Date'].max().to_pydatetime()
            print(f"📅 Last report date in public CSV: {last_date.strftime('%Y-%m-%d')}")
        else:
            print("ℹ️  No existing CSV data (first run)")
    except Exception as e:
        print(f"⚠️  Could not read CSV from public URL: {e}")
    
    # Get cloud PDF list
    cloud_pdfs = list_cloud_files('reports/')
    cloud_pdf_names = {Path(p).name for p in cloud_pdfs}
    print(f"📦 Found {len(cloud_pdf_names)} PDFs in cloud")
    
    # Determine start date for download
    download_start_date = _calculate_download_start_date(last_date, cloud_pdf_names)
    
    return download_start_date, cloud_pdf_names


def _calculate_download_start_date(last_date: datetime | None, cloud_pdf_names: set[str]) -> datetime:
    """Calculate the start date for downloading PDFs."""
    # Get latest date from cloud PDFs
    latest_cloud_date = None
    if cloud_pdf_names:
        cloud_dates = []
        for pdf_name in cloud_pdf_names:
            try:
                # Format: EarningsInsight_YYYYMMDD_MMDDYY.pdf
                parts = pdf_name.replace('.pdf', '').split('_')
                if len(parts) >= 2:
                    date_str = parts[1]  # YYYYMMDD
                    pdf_date = datetime.strptime(date_str, '%Y%m%d')
                    cloud_dates.append(pdf_date)
            except (ValueError, IndexError):
                continue
        
        if cloud_dates:
            latest_cloud_date = max(cloud_dates)
    
    # Use the latest date between CSV and cloud PDFs
    if last_date and latest_cloud_date:
        download_start_date = max(last_date, latest_cloud_date) + timedelta(days=1)
        print(f"📅 Last CSV date: {last_date.strftime('%Y-%m-%d')}")
        print(f"📅 Latest cloud PDF date: {latest_cloud_date.strftime('%Y-%m-%d')}")
        print(f"📅 Will download PDFs from: {download_start_date.strftime('%Y-%m-%d')}")
    elif last_date:
        download_start_date = last_date + timedelta(days=1)
        print(f"📅 Last CSV date: {last_date.strftime('%Y-%m-%d')}")
        print(f"📅 Will download PDFs from: {download_start_date.strftime('%Y-%m-%d')}")
    elif latest_cloud_date:
        download_start_date = latest_cloud_date + timedelta(days=1)
        print(f"📅 Latest cloud PDF date: {latest_cloud_date.strftime('%Y-%m-%d')}")
        print(f"📅 Will download PDFs from: {download_start_date.strftime('%Y-%m-%d')}")
    else:
        # First run: start from 2016
        download_start_date = datetime(2016, 1, 1)
        print(f"📅 No existing data found. Starting from: {download_start_date.strftime('%Y-%m-%d')}")
    
    return download_start_date

