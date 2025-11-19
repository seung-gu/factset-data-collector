"""GitHub Actions workflow: Complete data collection pipeline.

This script runs the full workflow:
1. Check for new PDFs (reads last date from public URL CSV)
2. Download new PDFs if available
3. Extract EPS chart pages as PNGs
4. Process images and extract data (auto-uploads CSV to public bucket)
5. Upload PDF/PNG to private bucket
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.factset_data_collector import download_pdfs, extract_charts, process_images
from src.factset_data_collector.utils import (
    CLOUD_STORAGE_ENABLED,
    list_cloud_files,
    upload_to_cloud,
)
import pandas as pd


def main():
    """Run complete data collection workflow."""
    print("=" * 80)
    print("🚀 FactSet Data Collection Workflow")
    print("=" * 80)
    print()
    
    # Only run cloud workflow in CI environment
    if not CLOUD_STORAGE_ENABLED:
        print("⚠️  Cloud storage not enabled. This workflow is for CI environment only.")
        print("   For local execution, use individual scripts or main.py")
        return
    
    # Step 1: Check for new PDFs
    print("-" * 80)
    print(" 🔍 Step 1: Checking for new PDFs...")
    
    # Get last date from public URL CSV
    last_date = None
    try:
        from src.factset_data_collector.utils.cloudflare import read_csv_from_cloud
        
        # Read directly from public URL
        df = read_csv_from_cloud("extracted_estimates.csv")
        
        if df is not None and not df.empty and 'Report_Date' in df.columns:
            df['Report_Date'] = pd.to_datetime(df['Report_Date'])
            last_date = df['Report_Date'].max().to_pydatetime()
            print(f"📅 Last report date in public CSV: {last_date.strftime('%Y-%m-%d')}")
        else:
            print("ℹ️  No existing CSV data (first run)")
    except Exception as e:
        print(f"⚠️  Could not read CSV from public URL: {e}")
    
    # Get cloud PDF list to determine latest date
    cloud_pdfs = list_cloud_files('reports/')
    cloud_pdf_names = {Path(p).name for p in cloud_pdfs}
    print(f"📦 Found {len(cloud_pdf_names)} PDFs in cloud")
    
    # Determine start date for download
    # Use the latest date from CSV or cloud PDFs
    download_start_date = None
    
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
    
    # Download new PDFs from FactSet
    print("-" * 80)
    print(" 📥 Step 2: Downloading new PDFs from FactSet...")
    
    try:
        pdf_dir = PROJECT_ROOT / "output" / "factset_pdfs"
        pdfs = download_pdfs(
            start_date=download_start_date,
            end_date=datetime.now(),
            outpath=pdf_dir,
            rate_limit=0.05
        )
        
        # Check if any new PDFs were downloaded
        local_pdfs = list(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []
        new_pdfs = [p for p in local_pdfs if p.name not in cloud_pdf_names]
        
        if not new_pdfs:
            print("\n✅ No new PDFs to process. Workflow complete!")
            return
        
        print(f"✅ Downloaded {len(new_pdfs)} new PDF(s)\n")
    except Exception as e:
        print(f"❌ PDF download failed: {e}\n")
        return
    
    # Step 3: Extract PNGs
    print("-" * 80)
    print(" 🖼️  Step 3: Extracting EPS chart pages...")
    
    try:
        estimates_dir = PROJECT_ROOT / "output" / "estimates"
        charts = extract_charts(local_pdfs, outpath=estimates_dir)
        print(f"✅ PNG extraction complete: {len(charts)} charts\n")
    except Exception as e:
        print(f"❌ PNG extraction failed: {e}\n")
        return
    
    # Step 4: Process images (returns DataFrame, doesn't save to file)
    print("-" * 80)
    print(" 🔍 Step 4: Processing images and extracting data...")
    
    try:
        df = process_images(directory=estimates_dir)
        print(f"✅ Image processing complete: {len(df)} records\n")
    except Exception as e:
        print(f"❌ Image processing failed: {e}\n")
        return
    
    # Step 5: Upload to cloud
    print("-" * 80)
    print(" ☁️  Step 5: Uploading results to cloud...")
    
    # Upload new PDFs
    uploaded_pdfs = 0
    if pdf_dir.exists():
        for pdf_file in pdf_dir.glob("*.pdf"):
            if pdf_file.name not in cloud_pdf_names:
                cloud_path = f"reports/{pdf_file.name}"
                if upload_to_cloud(pdf_file, cloud_path):
                    uploaded_pdfs += 1
    print(f"✅ Uploaded {uploaded_pdfs} PDF(s) to cloud")
    
    # Upload new PNGs
    uploaded_pngs = 0
    if estimates_dir.exists():
        cloud_pngs = {Path(p).name for p in list_cloud_files('estimates/')}
        for png_file in estimates_dir.glob("*.png"):
            if png_file.name not in cloud_pngs:
                cloud_path = f"estimates/{png_file.name}"
                if upload_to_cloud(png_file, cloud_path):
                    uploaded_pngs += 1
    print(f"✅ Uploaded {uploaded_pngs} PNG(s) to cloud")
    
    # Upload CSV to public bucket
    from src.factset_data_collector.utils.cloudflare import write_csv_to_cloud
    
    if write_csv_to_cloud(df, "extracted_estimates.csv"):
        print("✅ Uploaded extracted_estimates.csv to public bucket")
    else:
        print("⚠️  Failed to upload CSV to public bucket")
    
    print()
    print("=" * 80)
    print("✨ Workflow complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
