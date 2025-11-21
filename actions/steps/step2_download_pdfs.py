"""Step 2: Download new PDFs from FactSet."""

from datetime import datetime
from pathlib import Path

from src.eps_estimates_collector import download_pdfs


def download_new_pdfs(
    start_date: datetime,
    end_date: datetime,
    skip_existing: set[str]
) -> list[dict]:
    """
    Download new PDFs from FactSet.
    
    Args:
        start_date: Start date for downloading
        end_date: End date for downloading
        skip_existing: Set of PDF filenames to skip
        
    Returns:
        List of PDF info dicts with 'filename' and 'content' keys
    """
    print("-" * 80)
    print(" 📥 Step 2: Downloading new PDFs...")
    
    pdfs = download_pdfs(
        start_date=start_date,
        end_date=end_date,
        rate_limit=0.05,
        skip_existing=skip_existing
    )
    
    if not pdfs:
        print("\n✅ No new PDFs to process. Skipping Steps 3-5.")
    else:
        print(f"✅ Downloaded {len(pdfs)} new PDF(s)\n")
    
    return pdfs

