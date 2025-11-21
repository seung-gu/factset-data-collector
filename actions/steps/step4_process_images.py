"""Step 4: Process images and extract EPS data."""

from pathlib import Path
import pandas as pd

from src.eps_estimates_collector import process_images


def process_chart_images(directory: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Process chart images and extract EPS data.
    
    Args:
        directory: Directory containing chart images
        
    Returns:
        Tuple of (main_df, confidence_df)
    """
    print("-" * 80)
    print(" 🔍 Step 4: Processing images and extracting data...")
    
    df_main, df_confidence = process_images(directory=directory)
    print(f"✅ Image processing complete: {len(df_main)} records\n")
    
    return df_main, df_confidence

