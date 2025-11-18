"""Main processor for extracting quarters and values from chart images."""

import logging
from datetime import datetime, timedelta
from pathlib import Path

import cv2
import pandas as pd

from .bar_classifier import classify_all_bars
from .coordinate_matcher import match_quarters_with_numbers
from .google_vision_processor import extract_text_from_image, extract_text_with_boxes
from .parser import (
    extract_quarter_eps_pairs,
    get_report_date_from_filename
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_image(
    image_path: Path,
    use_coordinate_matching: bool = True,
    classify_bars: bool = True,
    use_multiple_methods: bool = True
) -> list[dict]:
    """Extract quarter and EPS information from a single image.
    
    Args:
        image_path: Image file path
        use_coordinate_matching: Whether to use coordinate-based matching (default: True)
        classify_bars: Whether to perform bar graph classification (default: True)
        use_multiple_methods: Whether to use all 3 methods for bar classification (default: True)
        
    Returns:
        List of dictionaries containing quarter and EPS information
    """
    try:
        # Perform OCR
        ocr_results = extract_text_with_boxes(image_path)
        logger.debug(f"OCR results count: {len(ocr_results)}")
        
        if not ocr_results:
            logger.warning(f"No OCR results for image: {image_path}")
            return []
        
        if use_coordinate_matching:
            # Coordinate-based matching
            matched_results = match_quarters_with_numbers(ocr_results)
            logger.debug(f"Matched results count: {len(matched_results)}")
            
            if classify_bars:
                # Bar graph classification
                image = cv2.imread(str(image_path))
                if image is None:
                    logger.error(f"Cannot read image: {image_path}")
                    return []
                
                matched_results = classify_all_bars(
                    image,
                    matched_results,
                    use_multiple_methods=use_multiple_methods
                )
            
            results = matched_results
        else:
            # Legacy method (text-based parsing)
            text = extract_text_from_image(image_path)
            results = extract_quarter_eps_pairs(text)
        
        if not results:
            logger.warning(f"No matched results for image: {image_path}")
            return []
        
        # Add report date
        report_date = get_report_date_from_filename(image_path.name)
        
        # Organize results
        processed_results = []
        for result in results:
            processed_result = {
                'report_date': report_date,
                'quarter': result.get('quarter', ''),
                'eps': result.get('eps', 0.0),
                'is_estimate': True  # Values extracted from images are considered estimates
            }
            
            # Add bar graph classification information (if available)
            if 'bar_color' in result:
                processed_result['bar_color'] = result['bar_color']
            if 'bar_confidence' in result:
                processed_result['bar_confidence'] = result['bar_confidence']
            
            processed_results.append(processed_result)
        
        return processed_results
    
    except Exception as e:
        logger.error(f"Error processing image: {image_path} - {e}", exc_info=True)
        return []


def process_directory(
    directory: Path,
    output_csv: Path | None = None,
    use_coordinate_matching: bool = True,
    classify_bars: bool = True,
    use_multiple_methods: bool = True,
    limit: int | None = None
) -> pd.DataFrame:
    """Process all images in a directory.
    
    Args:
        directory: Directory path containing images
        output_csv: CSV file path to save results (None to skip saving)
        use_coordinate_matching: Whether to use coordinate-based matching
        classify_bars: Whether to perform bar graph classification
        use_multiple_methods: Whether to use all 3 methods for bar classification
        limit: Maximum number of images to process (None to process all)
        
    Returns:
        DataFrame containing extracted data
    """
    # Load existing CSV to check processed dates (local only)
    existing_df = None
    processed_dates = set()
    if output_csv and output_csv.exists():
        try:
            existing_df = pd.read_csv(output_csv)
            existing_df = existing_df.drop(columns=['Confidence'], errors='ignore')
            if not existing_df.empty:
                existing_df['Report_Date'] = pd.to_datetime(existing_df['Report_Date'])
                processed_dates = set(existing_df['Report_Date'].dt.strftime('%Y%m%d'))
                logger.info(f"Found existing CSV with {len(existing_df)} records")
        except Exception as e:
            logger.warning(f"Could not read existing CSV: {e}")
    
    # Filter images: only process new ones
    image_files = [img for img in sorted(directory.glob('*.png')) if img.stem not in processed_dates]
    
    if limit:
        image_files = image_files[:limit]
    if not image_files:
        if not existing_df and not list(directory.glob('*.png')):
            print(f"\n⚠️  No PNG images found in {directory}")
            print(f"   Please run 'uv run python scripts/data_collection/extract_eps_charts.py' first to extract PNGs from PDFs.")
        return existing_df if existing_df is not None else pd.DataFrame(columns=['Report_Date'])
    
    total_images = len(image_files)
    print(f"\n🔄 Processing {total_images} new images...")
    logger.info(f"Processing {total_images} new images")
    
    current_df = existing_df.copy() if existing_df is not None and not existing_df.empty else pd.DataFrame()
    confidence_csv = output_csv.parent / f"{output_csv.stem}_confidence.csv" if output_csv else None
    
    # Load existing confidence CSV if it exists
    current_confidence_df = pd.DataFrame()
    if confidence_csv and confidence_csv.exists():
        try:
            current_confidence_df = pd.read_csv(confidence_csv)
            if not current_confidence_df.empty:
                current_confidence_df['Report_Date'] = pd.to_datetime(current_confidence_df['Report_Date'])
        except Exception as e:
            logger.warning(f"Could not read existing confidence CSV: {e}")
    
    for idx, image_path in enumerate(image_files, 1):
        print(f"[{idx}/{total_images}] {image_path.name}", end=" ... ")
        
        try:
            results = process_image(image_path, use_coordinate_matching, classify_bars, use_multiple_methods)
            if not results:
                logger.warning(f"No data extracted from {image_path.name}")
                print("⚠️  No data")
                continue
            
            df_wide = convert_to_wide_format(pd.DataFrame(results))
            df_confidence = calculate_confidence_dataframe(df_wide, pd.DataFrame(results))
            
            # Merge
            if current_df.empty:
                current_df = df_wide
                # Sort quarter columns consistently
                quarter_cols = sorted([c for c in current_df.columns if c != 'Report_Date'], key=_parse_quarter_for_sort)
                current_df = current_df[['Report_Date'] + quarter_cols]
            else:
                df_wide['Report_Date'] = pd.to_datetime(df_wide['Report_Date'])
                current_df['Report_Date'] = pd.to_datetime(current_df['Report_Date'])
                current_df = pd.concat([current_df, df_wide], ignore_index=True).drop_duplicates(subset=['Report_Date'], keep='last').sort_values('Report_Date').reset_index(drop=True)
                quarter_cols = sorted([c for c in current_df.columns if c != 'Report_Date'], key=_parse_quarter_for_sort)
                current_df = current_df[['Report_Date'] + quarter_cols]
            
            # Save (local only)
            if output_csv:
                current_df['Report_Date'] = pd.to_datetime(current_df['Report_Date'])
                df_to_save = current_df.copy().assign(Report_Date=lambda x: x['Report_Date'].dt.strftime('%Y-%m-%d'))
                df_to_save.to_csv(output_csv, index=False)
                
                # Confidence CSV: merge and deduplicate (same as main CSV)
                df_confidence['Report_Date'] = pd.to_datetime(df_confidence['Report_Date'])
                if current_confidence_df.empty:
                    current_confidence_df = df_confidence
                else:
                    current_confidence_df = pd.concat([current_confidence_df, df_confidence], ignore_index=True).drop_duplicates(subset=['Report_Date'], keep='last').sort_values('Report_Date').reset_index(drop=True)
                
                df_confidence_to_save = current_confidence_df.copy().assign(Report_Date=lambda x: x['Report_Date'].dt.strftime('%Y-%m-%d'))
                df_confidence_to_save.to_csv(confidence_csv, index=False)
                print(f"✅ {len(current_df)} records")
                
        except Exception as e:
            print(f"❌ {e}")
            logger.error(f"Error processing {image_path}: {e}")
    
    print(f"\n📊 Complete: {len(current_df)} total records\n")
    
    if current_df.empty:
        return existing_df if existing_df is not None else pd.DataFrame(columns=['Report_Date'])
    
    current_df['Report_Date'] = pd.to_datetime(current_df['Report_Date']).dt.strftime('%Y-%m-%d')
    return current_df


def convert_to_wide_format(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Long format DataFrame to wide format.
    
    Args:
        df: Long format DataFrame (report_date, quarter, eps, ...)
        
    Returns:
        Wide format DataFrame (Report_Date, Q1'14, Q2'14, ..., Confidence)
    """
    if df.empty:
        return pd.DataFrame(columns=['Report_Date'])
    
    # Add * to EPS values (if bar_color is 'light', mark as estimate)
    df = df.copy()
    if 'bar_color' in df.columns:
        # Light bar graphs are marked as estimates (* added)
        df['eps_str'] = df.apply(
            lambda row: f"{row['eps']}*" if row.get('bar_color') == 'light' else str(row['eps']),
            axis=1
        )
    else:
        df['eps_str'] = df['eps'].astype(str)
    
    # Convert to wide format using pivot
    df_pivot = df.pivot_table(
        index='report_date',
        columns='quarter',
        values='eps_str',
        aggfunc='first'  # Use first value if multiple combinations exist
    )
    
    # Convert index to column
    df_pivot = df_pivot.reset_index()
    df_pivot.columns.name = None
    
    # Rename column: report_date -> Report_Date
    df_pivot = df_pivot.rename(columns={'report_date': 'Report_Date'})
    
    # Sort quarter columns (Q1'14, Q2'14, ... order)
    quarter_columns = sorted(
        [col for col in df_pivot.columns if col != 'Report_Date'],
        key=lambda x: _parse_quarter_for_sort(x)
    )
    
    # Column order: Report_Date, Q1'14, Q2'14, ...
    df_pivot = df_pivot[['Report_Date'] + quarter_columns]
    
    # Convert empty values to empty strings (display as empty cells in CSV)
    df_pivot = df_pivot.fillna('')
    
    return df_pivot


def calculate_confidence_dataframe(df_wide: pd.DataFrame, df_long: pd.DataFrame) -> pd.DataFrame:
    """Calculate confidence and return as separate DataFrame.
    
    Args:
        df_wide: Wide format DataFrame (Report_Date, Quarter columns)
        df_long: Long format DataFrame (original data, includes bar_confidence, bar_color)
        
    Returns:
        DataFrame with Report_Date and Confidence columns
    """
    # Calculate confidence for each report_date
    confidences = []
    report_dates = []
    
    # Sort dates to identify first data point
    sorted_dates = sorted(df_wide['Report_Date'].unique())
    first_date = sorted_dates[0] if sorted_dates else None
    
    for report_date in df_wide['Report_Date']:
        # Filter data for this date only
        date_data = df_long[df_long['report_date'] == report_date].copy()
        
        if date_data.empty:
            confidences.append(0.0)
            report_dates.append(report_date)
            continue
        
        # 1. Calculate bar confidence score (3/3 match = 100%, 2/3 = 67%, 1/3 = 33%)
        bar_confidences = []
        if 'bar_confidence' in date_data.columns:
            for conf in date_data['bar_confidence']:
                if conf == 'high':
                    bar_confidences.append(100.0)
                elif conf == 'medium':
                    bar_confidences.append(67.0)
                elif conf == 'low':
                    bar_confidences.append(33.0)
                else:
                    bar_confidences.append(0.0)
        
        if bar_confidences:
            bar_score = sum(bar_confidences) / len(bar_confidences)
        else:
            bar_score = 0.0
        
        # 2. Calculate consistency with previous week's data (actuals only)
        # First data point excludes previous week comparison
        if report_date == first_date:
            # First data point uses only bar confidence (no previous week comparison)
            consistency_score = 100.0  # Treat as 100% since no previous week comparison
        else:
            consistency_score = calculate_consistency_with_previous_week(
                report_date, date_data, df_long
            )
        
        # 3. Calculate combined confidence (weighted average)
        # Bar graph consistency weight: 0.5, previous week consistency weight: 0.5
        final_confidence = (bar_score * 0.5) + (consistency_score * 0.5)
        
        confidences.append(round(final_confidence, 1))
        report_dates.append(report_date)
    
    # Create DataFrame with Report_Date and Confidence
    df_confidence = pd.DataFrame({
        'Report_Date': report_dates,
        'Confidence': confidences
    })
    
    return df_confidence


def calculate_consistency_with_previous_week(
    current_date: str,
    current_data: pd.DataFrame,
    all_data: pd.DataFrame
) -> float:
    """Calculate consistency with the closest previous data (actuals only).
    
    Args:
        current_date: Current report date (YYYY-MM-DD)
        current_data: Data for current date
        all_data: All data
        
    Returns:
        Consistency rate (0-100)
    """
    try:
        # Parse date
        current_dt = datetime.strptime(current_date, '%Y-%m-%d')
        
        # Find all dates before current date
        all_dates = pd.to_datetime(all_data['report_date'].unique())
        previous_dates = all_dates[all_dates < current_dt]
        
        if len(previous_dates) == 0:
            return 0.0
        
        # Find closest previous date
        previous_date = previous_dates.max().strftime('%Y-%m-%d')
        
        # Find previous data
        previous_data = all_data[all_data['report_date'] == previous_date].copy()
        
        if previous_data.empty:
            return 0.0
        
        # Filter actuals only (bar_color is 'dark')
        current_actual = current_data[current_data.get('bar_color', '') == 'dark'].copy()
        previous_actual = previous_data[previous_data.get('bar_color', '') == 'dark'].copy()
        
        if current_actual.empty or previous_actual.empty:
            return 0.0
        
        # Compare EPS values for same quarters
        matches = 0
        total_comparisons = 0
        
        for _, current_row in current_actual.iterrows():
            quarter = current_row['quarter']
            current_eps = current_row['eps']
            
            # Find same quarter in previous week's data
            prev_row = previous_actual[previous_actual['quarter'] == quarter]
            
            if not prev_row.empty:
                previous_eps = prev_row.iloc[0]['eps']
                total_comparisons += 1
                
                # Check if 80% or more match (allow 5% error)
                if abs(current_eps - previous_eps) / max(abs(previous_eps), 0.01) <= 0.2:
                    matches += 1
        
        if total_comparisons == 0:
            return 0.0
        
        # Calculate consistency rate (0-100)
        consistency = (matches / total_comparisons) * 100.0
        
        return consistency
    
    except (ValueError, KeyError) as e:
        logger.warning(f"Error calculating consistency ({current_date}): {e}")
        return 0.0


def _parse_quarter_for_sort(quarter: str) -> tuple[int, int]:
    """Convert quarter string to tuple for sorting.
    
    Args:
        quarter: Quarter string (e.g., "Q1'14", "Q2'15")
        
    Returns:
        (year, quarter) tuple (e.g., (2014, 1), (2015, 2))
    """
    try:
        # Parse Q1'14 format
        if "'" in quarter:
            q_part, year_part = quarter.split("'")
            q_num = int(q_part[1:])  # Q1 -> 1
            year = 2000 + int(year_part)  # '14 -> 2014
        else:
            # Parse Q114 format
            q_num = int(quarter[1])
            year = 2000 + int(quarter[2:4])
        
        return (year, q_num)
    except (ValueError, IndexError):
        # Return (0, 0) on parse failure to sort at the beginning
        return (0, 0)