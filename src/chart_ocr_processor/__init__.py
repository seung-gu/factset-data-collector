"""FactSet Data Collector - Package for extracting quarterly EPS estimates from FactSet Earnings Insight reports."""

from .processor import process_directory, process_image
from .google_vision_processor import extract_text_from_image, extract_text_with_boxes
from .parser import parse_quarter, parse_number, get_report_date_from_filename

__version__ = "0.1.0"

__all__ = [
    'process_directory',
    'process_image',
    'extract_text_from_image',
    'extract_text_with_boxes',
    'parse_quarter',
    'parse_number',
    'get_report_date_from_filename',
]
