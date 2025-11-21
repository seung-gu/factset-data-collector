"""Step 3: Extract EPS chart pages as PNGs from PDFs."""

from pathlib import Path

from src.eps_estimates_collector import extract_charts


def extract_chart_pages(pdf_files: list[Path]) -> list[tuple[str, bytes]]:
    """
    Extract EPS chart pages as PNGs from PDFs.
    
    Args:
        pdf_files: List of PDF file paths
        
    Returns:
        List of tuples (filename, image_bytes)
    """
    print("-" * 80)
    print(" 🖼️  Step 3: Extracting EPS chart pages...")
    
    chart_data = extract_charts(pdf_files)
    print(f"✅ PNG extraction complete: {len(chart_data)} charts\n")
    
    return chart_data

