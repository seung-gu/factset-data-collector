"""GitHub Actions workflow: Complete data collection pipeline.

This script runs the full workflow:
1. Download CSV from cloud
2. Check for new PDFs
3. Download new PDFs if available
4. Extract EPS chart pages as PNGs
5. Process images and extract data to CSV
6. Upload results to cloud
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data_collection.download_factset_pdfs import download_factset_pdfs, main as download_main
from scripts.data_collection.extract_eps_charts import main as extract_main
from src.chart_ocr_processor.processor import process_directory
from src.service.cloudflare import (
    CLOUD_STORAGE_ENABLED,
    download_from_cloud,
    list_cloud_files,
    upload_to_cloud,
)


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
    
    # Step 0: Download CSV from cloud
    print("\n\n📥 Step 0: Downloading CSV from cloud...")
    print("-" * 80)
    csv_file = PROJECT_ROOT / "output" / "extracted_estimates.csv"
    confidence_csv_file = PROJECT_ROOT / "output" / "extracted_estimates_confidence.csv"
    
    csv_downloaded = download_from_cloud("extracted_estimates.csv", csv_file)
    confidence_downloaded = download_from_cloud("extracted_estimates_confidence.csv", confidence_csv_file)
    
    if csv_downloaded:
        print(f"✅ Downloaded CSV from cloud: {csv_file}")
    else:
        print("ℹ️  No CSV found in cloud (first run)")
    
    if confidence_downloaded:
        print(f"✅ Downloaded confidence CSV from cloud: {confidence_csv_file}")
    else:
        print("ℹ️  No confidence CSV found in cloud (first run)")
    
    print()
    
    # Step 1: Check for new PDFs
    print("\n\n🔍 Step 1: Checking for new PDFs...")
    print("-" * 80)
    
    # Get last date from CSV
    last_date = None
    if csv_file.exists():
        try:
            import pandas as pd
            df = pd.read_csv(csv_file)
            if not df.empty and 'Report_Date' in df.columns:
                df['Report_Date'] = pd.to_datetime(df['Report_Date'])
                last_date = df['Report_Date'].max().to_pydatetime()
                print(f"📅 Last report date in CSV: {last_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            print(f"⚠️  Could not read CSV: {e}")
    
    # Get cloud PDF list
    cloud_pdfs = list_cloud_files('reports/')
    cloud_pdf_names = {Path(p).name for p in cloud_pdfs}
    print(f"📦 Found {len(cloud_pdf_names)} PDFs in cloud")
    
    # Download new PDFs
    print("\n\n📥 Step 2: Downloading new PDFs from FactSet...")
    print("-" * 80)
    try:
        download_main()
        
        # Check if any new PDFs were downloaded
        local_pdf_dir = PROJECT_ROOT / "output" / "factset_pdfs"
        local_pdfs = list(local_pdf_dir.glob("*.pdf")) if local_pdf_dir.exists() else []
        new_pdfs = [p for p in local_pdfs if p.name not in cloud_pdf_names]
        
        if not new_pdfs:
            print("\n✅ No new PDFs to process. Workflow complete!")
            return
        
        print(f"✅ Downloaded {len(new_pdfs)} new PDF(s)\n")
    except Exception as e:
        print(f"❌ PDF download failed: {e}\n")
        return
    
    # Step 3: Extract PNGs
    print("\n\n 🖼️  Step 3: Extracting EPS chart pages...")
    print("-" * 80)
    try:
        extract_main()
        print("✅ PNG extraction complete\n")
    except Exception as e:
        print(f"❌ PNG extraction failed: {e}\n")
        return
    
    # Step 4: Process images
    print("\n\n 🔍 Step 4: Processing images and extracting data...")
    print("-" * 80)
    try:
        # Set logging level to INFO for better visibility
        import logging
        logging.basicConfig(level=logging.INFO)
        
        estimates_dir = PROJECT_ROOT / "output" / "estimates"
        output_csv = PROJECT_ROOT / "output" / "extracted_estimates.csv"
        
        # Check if Google Cloud credentials are set
        google_creds = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if google_creds:
            print(f"✅ Google Cloud credentials found: {google_creds}")
            if Path(google_creds).exists():
                print(f"✅ Credentials file exists")
            else:
                print(f"⚠️  Credentials file not found at: {google_creds}")
        else:
            print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
        
        df = process_directory(
            directory=estimates_dir,
            output_csv=output_csv,
            use_coordinate_matching=True,
            classify_bars=True,
            use_multiple_methods=True
        )
        print(f"✅ Image processing complete: {len(df)} records\n")
    except Exception as e:
        print(f"❌ Image processing failed: {e}\n")
        return
    
    # Step 5: Upload to cloud
    print("\n\n☁️  Step 5: Uploading results to cloud...")
    print("-" * 80)
    
    # Upload new PDFs
    pdf_dir = PROJECT_ROOT / "output" / "factset_pdfs"
    uploaded_pdfs = 0
    if pdf_dir.exists():
        for pdf_file in pdf_dir.glob("*.pdf"):
            if pdf_file.name not in cloud_pdf_names:
                cloud_path = f"reports/{pdf_file.name}"
                if upload_to_cloud(pdf_file, cloud_path):
                    uploaded_pdfs += 1
    print(f"✅ Uploaded {uploaded_pdfs} PDF(s) to cloud")
    
    # Upload new PNGs
    png_dir = PROJECT_ROOT / "output" / "estimates"
    uploaded_pngs = 0
    if png_dir.exists():
        cloud_pngs = {Path(p).name for p in list_cloud_files('estimates/')}
        for png_file in png_dir.glob("*.png"):
            if png_file.name not in cloud_pngs:
                cloud_path = f"estimates/{png_file.name}"
                if upload_to_cloud(png_file, cloud_path):
                    uploaded_pngs += 1
    print(f"✅ Uploaded {uploaded_pngs} PNG(s) to cloud")
    
    # Upload CSV files
    if csv_file.exists():
        if upload_to_cloud(csv_file, "extracted_estimates.csv"):
            print("✅ Uploaded CSV to cloud")
    
    if confidence_csv_file.exists():
        if upload_to_cloud(confidence_csv_file, "extracted_estimates_confidence.csv"):
            print("✅ Uploaded confidence CSV to cloud")
    
    print()
    print("=" * 80)
    print("✨ Workflow complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()

