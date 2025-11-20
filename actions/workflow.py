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

from src.eps_estimates_collector import download_pdfs, extract_charts, process_images
from src.eps_estimates_collector.utils import (
    CLOUD_STORAGE_ENABLED,
    list_cloud_files,
    upload_to_cloud,
)
from src.eps_estimates_collector.utils.cloudflare import write_csv_to_cloud, upload_file_to_public_cloud
import pandas as pd


def main():
    """Run complete data collection workflow."""
    print("=" * 80)
    print("🚀 EPS Estimates Collection Workflow")
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
        from src.eps_estimates_collector.utils.cloudflare import read_csv_from_cloud
        
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
    
    # Download new PDFs
    print("-" * 80)
    print(" 📥 Step 2: Downloading new PDFs...")
    
    import tempfile
    
    try:
        pdfs = download_pdfs(
            start_date=download_start_date,
            end_date=datetime.now(),
            rate_limit=0.05,
            skip_existing=cloud_pdf_names
        )
        
        if not pdfs:
            print("\n✅ No new PDFs to process. Skipping Steps 2-5.")
        else:
            print(f"✅ Downloaded {len(pdfs)} new PDF(s)\n")
            
            # Save PDFs to temp files and extract PNGs
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                pdf_files = []
                
                for pdf_info in pdfs:
                    pdf_path = tmp_path / pdf_info['filename']
                    pdf_path.write_bytes(pdf_info['content'])
                    pdf_files.append(pdf_path)
                
                # Step 3: Extract PNGs
                print("-" * 80)
                print(" 🖼️  Step 3: Extracting EPS chart pages...")
                
                chart_data = extract_charts(pdf_files)
                print(f"✅ PNG extraction complete: {len(chart_data)} charts\n")
                
                # Save PNGs to temp files for processing
                chart_files = []
                for filename, image_bytes in chart_data:
                    chart_path = tmp_path / filename
                    chart_path.write_bytes(image_bytes)
                    chart_files.append(chart_path)
                
                # Step 4: Process images
                print("-" * 80)
                print(" 🔍 Step 4: Processing images and extracting data...")
                df_main, df_confidence = process_images(directory=tmp_path)
                print(f"✅ Image processing complete: {len(df_main)} records\n")
                
                # Step 5: Upload to cloud
                print("-" * 80)
                print(" ☁️  Step 5: Uploading results to cloud...")
                
                failed_pdfs = [p.name for p in pdf_files if not upload_to_cloud(p, f"reports/{p.name}")]
                failed_pngs = [p.name for p in chart_files if not upload_to_cloud(p, f"estimates/{p.name}")]
                
                if failed_pdfs:
                    raise Exception(f"Failed to upload PDFs: {', '.join(failed_pdfs)}")
                if failed_pngs:
                    raise Exception(f"Failed to upload PNGs: {', '.join(failed_pngs)}")
                
                print(f"✅ Uploaded {len(pdf_files)} PDF(s), {len(chart_files)} PNG(s)")
                
                if not write_csv_to_cloud(df_main, "extracted_estimates.csv"):
                    raise Exception("Failed to upload extracted_estimates.csv")
                if not write_csv_to_cloud(df_confidence, "extracted_estimates_confidence.csv"):
                    raise Exception("Failed to upload extracted_estimates_confidence.csv") 
                
                print(f"✅ Uploaded extracted_estimates.csv and extracted_estimates_confidence.csv")
        
        # Step 6: Generate and upload P/E ratio plot to public bucket (always runs)
        print("-" * 80)
        print(" 📊 Step 6: Generating P/E ratio plot...")
        
        try:
            from src.eps_estimates_collector.analysis.pe_ratio import plot_pe_ratio_with_price
            
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                plot_path = tmp_path / "pe_ratio_plot.png"
                plot_pe_ratio_with_price(output_path=plot_path)
                
                # Upload to public bucket
                if upload_file_to_public_cloud(plot_path, "pe_ratio_plot.png"):
                    print("✅ Uploaded pe_ratio_plot.png to public bucket")
                else:
                    print("⚠️  Failed to upload pe_ratio_plot.png")
        except Exception as e:
            print(f"⚠️  Could not generate P/E ratio plot: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"❌ Workflow failed: {e}\n")
        import sys
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("✨ Workflow complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
