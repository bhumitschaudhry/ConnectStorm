#!/usr/bin/env python3
"""
File-Storm Storage Handler
Supports local storage and S3-compatible storage (AWS S3, Cloudflare R2).
"""

import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

# Storage configuration
STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')  # 'local' or 's3'

# S3 configuration
S3_ENDPOINT = os.getenv('S3_ENDPOINT')
S3_REGION = os.getenv('S3_REGION', 'us-east-1')
S3_BUCKET = os.getenv('S3_BUCKET')
S3_ACCESS_KEY = os.getenv('S3_ACCESS_KEY')
S3_SECRET_KEY = os.getenv('S3_SECRET_KEY')
S3_PUBLIC_BASE_URL = os.getenv('S3_PUBLIC_BASE_URL', '')

# Local storage configuration
LOCAL_STORAGE_DIR = os.getenv('LOCAL_STORAGE_DIR', '/tmp/filestorm_storage')


def get_s3_client():
    """
    Get configured S3 client (AWS S3 or Cloudflare R2).
    """
    if S3_ENDPOINT:
        # Custom endpoint (e.g., Cloudflare R2)
        return boto3.client(
            's3',
            endpoint_url=S3_ENDPOINT,
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION
        )
    else:
        # Standard AWS S3
        return boto3.client(
            's3',
            aws_access_key_id=S3_ACCESS_KEY,
            aws_secret_access_key=S3_SECRET_KEY,
            region_name=S3_REGION
        )


def upload_to_s3(file_path, object_name):
    """
    Upload file to S3-compatible storage.
    Returns public URL or object key.
    """
    try:
        s3_client = get_s3_client()
        
        # Upload file
        s3_client.upload_file(
            file_path,
            S3_BUCKET,
            object_name,
            ExtraArgs={'ContentType': 'application/octet-stream'}
        )
        
        # Generate URL
        if S3_PUBLIC_BASE_URL:
            # Use custom public base URL (for R2, etc.)
            url = f"{S3_PUBLIC_BASE_URL.rstrip('/')}/{object_name}"
        elif S3_ENDPOINT:
            # Custom endpoint URL
            url = f"{S3_ENDPOINT.rstrip('/')}/{S3_BUCKET}/{object_name}"
        else:
            # Standard S3 URL
            url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{object_name}"
        
        print(f"✓ Uploaded to S3: {url}")
        return url
        
    except ClientError as e:
        print(f"✗ S3 upload error: {e}")
        raise
    except Exception as e:
        print(f"✗ Unexpected error during S3 upload: {e}")
        raise


def upload_to_local(file_path, object_name):
    """
    Copy file to local storage directory.
    Returns local path.
    """
    try:
        # Ensure storage directory exists
        os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)
        
        # Destination path
        dest_path = os.path.join(LOCAL_STORAGE_DIR, object_name)
        
        # Copy file
        import shutil
        shutil.copy2(file_path, dest_path)
        
        print(f"✓ Saved locally: {dest_path}")
        return dest_path
        
    except Exception as e:
        print(f"✗ Local storage error: {e}")
        raise


def upload_file(file_path, original_filename):
    """
    Upload file to configured storage backend.
    Returns storage URL or path.
    """
    # Use original filename as object name
    object_name = original_filename
    
    if STORAGE_MODE == 's3':
        return upload_to_s3(file_path, object_name)
    else:
        return upload_to_local(file_path, object_name)


if __name__ == '__main__':
    # Test storage configuration
    print(f"Storage Mode: {STORAGE_MODE}")
    
    if STORAGE_MODE == 's3':
        print(f"S3 Endpoint: {S3_ENDPOINT or 'AWS S3 Default'}")
        print(f"S3 Bucket: {S3_BUCKET}")
        print(f"S3 Region: {S3_REGION}")
    else:
        print(f"Local Storage Directory: {LOCAL_STORAGE_DIR}")

