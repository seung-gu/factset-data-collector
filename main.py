"""Main execution script."""

import argparse
from pathlib import Path

from src.chart_ocr_processor.processor import process_directory


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Extract quarters and values from chart images.'
    )
    parser.add_argument(
        '--input-dir',
        type=str,
        default='output/estimates',
        help='Directory containing image files (default: output/estimates)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output/extracted_estimates.csv',
        help='CSV file path to save results (default: output/extracted_estimates.csv)'
    )
    parser.add_argument(
        '--no-coordinate-matching',
        action='store_true',
        help='Use text-based parsing instead of coordinate-based matching'
    )
    parser.add_argument(
        '--no-bar-classification',
        action='store_true',
        help='Do not perform bar graph classification'
    )
    parser.add_argument(
        '--single-method',
        action='store_true',
        help='Use single method for bar graph classification (do not use all 3 methods)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of images to process (for testing)'
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_file = Path(args.output)
    
    if not input_dir.exists():
        print(f"Error: Input directory does not exist: {input_dir}")
        return
    
    # Create output directory
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Execute processing
    df = process_directory(
        directory=input_dir,
        output_csv=output_file,
        use_coordinate_matching=not args.no_coordinate_matching,
        classify_bars=not args.no_bar_classification,
        use_multiple_methods=not args.single_method,
        limit=args.limit
    )
    
    print(f"\nProcessing complete: Extracted {len(df)} records.")
    print(f"Result file: {output_file}")


if __name__ == '__main__':
    main()
