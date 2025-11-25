"""GitHub Actions workflow: Complete data collection pipeline.

This script runs the full workflow:
1. Check for new PDFs (reads last date from public URL CSV)
2. Download new PDFs if available
3. Extract EPS chart pages as PNGs
4. Process images and extract data (auto-uploads CSV to public bucket)
5. Upload PDF/PNG to private bucket
6. Generate and upload P/E ratio plot
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.factset_report_analyzer.utils import CLOUD_STORAGE_ENABLED
from actions.steps import (
    check_for_new_pdfs,
    download_new_pdfs,
    extract_chart_pages,
    process_chart_images,
    upload_results_to_cloud,
    generate_pe_ratio_plot,
)


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
    
    try:
        # Step 1: Check for new PDFs
        download_start_date, cloud_pdf_names = check_for_new_pdfs()
        
        # Step 2: Download new PDFs
        pdfs = download_new_pdfs(
            start_date=download_start_date,
            end_date=datetime.now(),
            skip_existing=cloud_pdf_names
        )
        
        # Steps 3-5: Process PDFs if new ones were downloaded
        if pdfs:
            _process_new_pdfs(pdfs)
        
        # Step 6: Generate and upload P/E ratio plot (always runs)
        generate_pe_ratio_plot()
        
    except Exception as e:
        print(f"❌ Workflow failed: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print("=" * 80)
    print("✨ Workflow complete!")
    print("=" * 80)


def _process_new_pdfs(pdfs: list[dict]) -> None:
    """Process newly downloaded PDFs through steps 3-5."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Save PDFs to temp files
        pdf_files = []
        for pdf_info in pdfs:
            pdf_path = tmp_path / pdf_info['filename']
            pdf_path.write_bytes(pdf_info['content'])
            pdf_files.append(pdf_path)
        
        # Step 3: Extract chart pages
        chart_data = extract_chart_pages(pdf_files)
        
        # Save PNGs to temp files
        chart_files = []
        for filename, image_bytes in chart_data:
            chart_path = tmp_path / filename
            chart_path.write_bytes(image_bytes)
            chart_files.append(chart_path)
        
        # Step 4: Process images
        df_main, df_confidence = process_chart_images(tmp_path)
        
        # Step 5: Upload to cloud
        upload_results_to_cloud(pdf_files, chart_files, df_main, df_confidence)


if __name__ == '__main__':
    main()
