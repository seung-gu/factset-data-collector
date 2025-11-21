"""Step 5: Upload results to cloud storage."""

from pathlib import Path

from src.eps_estimates_collector.utils import upload_to_cloud
from src.eps_estimates_collector.utils.cloudflare import write_csv_to_cloud
import pandas as pd


def upload_results_to_cloud(
    pdf_files: list[Path],
    chart_files: list[Path],
    df_main: pd.DataFrame,
    df_confidence: pd.DataFrame
) -> None:
    """
    Upload PDFs, PNGs, and CSV results to cloud storage.
    
    Args:
        pdf_files: List of PDF file paths
        chart_files: List of chart image file paths
        df_main: Main extracted estimates DataFrame
        df_confidence: Confidence scores DataFrame
        
    Raises:
        Exception: If upload fails
    """
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

