#!/usr/bin/env python3
"""
File-Storm Selenium Producer
Simulates real users uploading files using Selenium WebDriver.
"""

import os
import sys
import time
import random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()

# Configuration
PRODUCER_TARGET_BASE_URL = os.getenv('PRODUCER_TARGET_BASE_URL', 'http://localhost:8080/upload')
PRODUCER_FILES_DIR = os.getenv('PRODUCER_FILES_DIR', 'files')
PRODUCER_USERS = int(os.getenv('PRODUCER_USERS', '5'))
PRODUCER_REPEATS = int(os.getenv('PRODUCER_REPEATS', '3'))
PRODUCER_HEADLESS = os.getenv('PRODUCER_HEADLESS', 'true').lower() == 'true'


def get_chrome_driver():
    """
    Create and configure Chrome WebDriver.
    """
    chrome_options = Options()
    
    if PRODUCER_HEADLESS:
        chrome_options.add_argument('--headless=new')  # New headless mode
    
    # Additional options for stability (especially on Render)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-software-rasterizer')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Create driver
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    
    return driver


def get_available_files():
    """
    Get list of files from the configured directory.
    """
    files_dir = Path(PRODUCER_FILES_DIR)
    
    if not files_dir.exists():
        print(f"⚠ Files directory '{PRODUCER_FILES_DIR}' does not exist")
        return []
    
    # Get all files (not directories)
    files = [f for f in files_dir.iterdir() if f.is_file()]
    
    if not files:
        print(f"⚠ No files found in '{PRODUCER_FILES_DIR}'")
    
    return files


def upload_file_selenium(user_id, file_path, attempt=1):
    """
    Upload a single file using Selenium.
    Simulates real user behavior.
    """
    driver = None
    
    try:
        # Create driver
        driver = get_chrome_driver()
        
        print(f"[User {user_id}] Opening upload page: {PRODUCER_TARGET_BASE_URL}")
        driver.get(PRODUCER_TARGET_BASE_URL)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        
        # Find file input
        file_input = driver.find_element(By.NAME, "file")
        
        # Upload file (provide absolute path)
        absolute_path = str(file_path.resolve())
        file_input.send_keys(absolute_path)
        
        print(f"[User {user_id}] Selected file: {file_path.name}")
        
        # Fill uploader ID field (if exists)
        try:
            uploader_input = driver.find_element(By.NAME, "uploader_id")
            uploader_input.clear()
            uploader_input.send_keys(f"user_{user_id}")
        except:
            pass  # Field might not exist
        
        # Small delay to simulate human behavior
        time.sleep(random.uniform(0.5, 1.5))
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        submit_button.click()
        
        print(f"[User {user_id}] Submitted upload for: {file_path.name}")
        
        # Wait a moment to ensure submission completes
        time.sleep(2)
        
        return True
        
    except Exception as e:
        print(f"✗ [User {user_id}] Upload failed (attempt {attempt}): {e}")
        return False
        
    finally:
        if driver:
            driver.quit()


def user_upload_session(user_id, files, num_uploads):
    """
    Simulates a user session uploading multiple files.
    """
    print(f"🚀 [User {user_id}] Starting session ({num_uploads} uploads)")
    
    successful_uploads = 0
    failed_uploads = 0
    
    for i in range(num_uploads):
        # Select a random file
        if not files:
            print(f"⚠ [User {user_id}] No files available to upload")
            break
        
        file_to_upload = random.choice(files)
        
        # Attempt upload
        success = upload_file_selenium(user_id, file_to_upload)
        
        if success:
            successful_uploads += 1
        else:
            failed_uploads += 1
        
        # Random delay between uploads to simulate real user behavior
        if i < num_uploads - 1:
            delay = random.uniform(2, 5)
            print(f"[User {user_id}] Waiting {delay:.1f}s before next upload...")
            time.sleep(delay)
    
    print(f"✓ [User {user_id}] Session complete: {successful_uploads} successful, {failed_uploads} failed")
    
    return {
        'user_id': user_id,
        'successful': successful_uploads,
        'failed': failed_uploads
    }


def run_producer():
    """
    Main producer function.
    Spawns multiple concurrent users uploading files.
    """
    print("🚀 File-Storm Selenium Producer")
    print(f"   Target URL: {PRODUCER_TARGET_BASE_URL}")
    print(f"   Files Directory: {PRODUCER_FILES_DIR}")
    print(f"   Concurrent Users: {PRODUCER_USERS}")
    print(f"   Uploads per User: {PRODUCER_REPEATS}")
    print(f"   Headless Mode: {PRODUCER_HEADLESS}")
    print()
    
    # Get available files
    files = get_available_files()
    
    if not files:
        print("✗ No files found to upload. Please add files to the 'files/' directory.")
        return
    
    print(f"✓ Found {len(files)} files to upload:")
    for f in files:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")
    print()
    
    # Run concurrent user sessions
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=PRODUCER_USERS) as executor:
        # Submit tasks
        futures = {
            executor.submit(user_upload_session, i+1, files, PRODUCER_REPEATS): i+1
            for i in range(PRODUCER_USERS)
        }
        
        # Collect results
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"✗ User session error: {e}")
    
    # Summary
    elapsed_time = time.time() - start_time
    total_successful = sum(r['successful'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    
    print()
    print("=" * 60)
    print("📊 PRODUCER SUMMARY")
    print("=" * 60)
    print(f"Total Users: {PRODUCER_USERS}")
    print(f"Successful Uploads: {total_successful}")
    print(f"Failed Uploads: {total_failed}")
    print(f"Total Time: {elapsed_time:.2f}s")
    print(f"Average Rate: {total_successful / elapsed_time:.2f} uploads/sec")
    print("=" * 60)


if __name__ == '__main__':
    try:
        run_producer()
    except KeyboardInterrupt:
        print("\n⚠ Producer interrupted by user")
    except Exception as e:
        print(f"✗ Producer error: {e}")
        sys.exit(1)

