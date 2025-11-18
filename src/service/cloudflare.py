"""Cloudflare R2 storage utilities for uploading files."""

import io
import os
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd

try:
    import boto3
    from botocore.config import Config
except ImportError:
    boto3 = None
    Config = None

load_dotenv()

# Cloudflare R2 settings
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', '')
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID', '')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '')

# Enable cloud storage only in CI environment (GitHub Actions) or if explicitly enabled
# Local execution: use local storage only
_cloud_storage_setting = os.getenv('CLOUD_STORAGE_ENABLED', '').lower()
_is_ci = os.getenv('CI', '').lower() == 'true'  # GitHub Actions sets CI=true

if _cloud_storage_setting == 'true':
    # Explicitly enabled
    CLOUD_STORAGE_ENABLED = bool(all([R2_BUCKET_NAME, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]))
elif _cloud_storage_setting == 'false':
    # Explicitly disabled
    CLOUD_STORAGE_ENABLED = False
elif _is_ci:
    # Auto-enable in CI environment if R2 credentials are present
    CLOUD_STORAGE_ENABLED = bool(all([R2_BUCKET_NAME, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]))
else:
    # Local execution: disable cloud storage
    CLOUD_STORAGE_ENABLED = False


def _get_s3_client():
    """Get configured S3 client for R2."""
    if not CLOUD_STORAGE_ENABLED:
        return None
    if not all([R2_BUCKET_NAME, R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
        return None
    
    if boto3 is None or Config is None:
        return None
    
    try:
        return boto3.client(
            's3',
            endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
    except ImportError:
        return None


def upload_to_cloud(file_path: Path, cloud_path: str | None = None) -> bool:
    """Upload file to Cloudflare R2.
    
    Args:
        file_path: Local file path
        cloud_path: Cloud storage path (if None, uses file_path.name)
        
    Returns:
        True if successful, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    if not file_path.exists():
        return False
    
    cloud_path = cloud_path or file_path.name
    
    try:
        s3_client.upload_file(str(file_path), R2_BUCKET_NAME, cloud_path)
        return True
    except Exception:
        # Silently fail - don't interrupt local file saving
        return False


def download_from_cloud(cloud_path: str, local_path: Path) -> bool:
    """Download file from Cloudflare R2.
    
    Args:
        cloud_path: Cloud storage path
        local_path: Local file path to save to
        
    Returns:
        True if successful, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        s3_client.download_file(R2_BUCKET_NAME, cloud_path, str(local_path))
        return True
    except Exception:
        return False


def read_csv_from_cloud(cloud_path: str) -> pd.DataFrame | None:
    """Read CSV file from Cloudflare R2.
    
    Args:
        cloud_path: Cloud storage path to CSV file
        
    Returns:
        DataFrame if successful, None otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return None
    
    try:
        response = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=cloud_path)
        return pd.read_csv(io.BytesIO(response['Body'].read()))
    except Exception:
        return None


def write_csv_to_cloud(df: pd.DataFrame, cloud_path: str) -> bool:
    """Write DataFrame to CSV file in Cloudflare R2.
    
    Args:
        df: DataFrame to write
        cloud_path: Cloud storage path for CSV file
        
    Returns:
        True if successful, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    try:
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        s3_client.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=cloud_path,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        return True
    except Exception:
        return False


def file_exists_in_cloud(cloud_path: str) -> bool:
    """Check if file exists in Cloudflare R2.
    
    Args:
        cloud_path: Cloud storage path
        
    Returns:
        True if file exists, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    try:
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=cloud_path)
        return True
    except Exception:
        return False


def list_cloud_files(prefix: str = '') -> list[str]:
    """List files in Cloudflare R2 bucket with given prefix.
    
    Args:
        prefix: Prefix to filter files (e.g., 'estimates/' for PNG files, 'reports/' for PDFs)
        
    Returns:
        List of file paths (keys) in cloud storage
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return []
    
    try:
        files = []
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=R2_BUCKET_NAME, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    files.append(obj['Key'])
        return files
    except Exception:
        return []

