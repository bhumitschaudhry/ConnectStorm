#!/usr/bin/env python3
import os
import sys
import time
import random
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
load_dotenv()
PRODUCER_TARGET_BASE_URL = os.getenv('PRODUCER_TARGET_BASE_URL', 'http://localhost:8080/upload')
PRODUCER_FILES_DIR = os.getenv('PRODUCER_FILES_DIR', 'files')
PRODUCER_USERS = int(os.getenv('PRODUCER_USERS', '5'))
PRODUCER_REPEATS = int(os.getenv('PRODUCER_REPEATS', '3'))
PRODUCER_HEADLESS = os.getenv('PRODUCER_HEADLESS', 'true').lower() == 'true'
def get_chrome_driver():
    # Set up Chrome options.
    chrome_options = Options()
    if PRODUCER_HEADLESS:
        chrome_options.add_argument('--headless=new')
    is_windows = sys.platform.startswith('win')
    is_linux = sys.platform.startswith('linux')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-extensions')
    chrome_options.add_argument('--disable-infobars')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    chrome_options.add_argument('--log-level=3')  
    chrome_options.add_argument('--silent')
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    chrome_options.add_argument('--disable-background-networking')
    chrome_options.add_argument('--disable-background-timer-throttling')
    chrome_options.add_argument('--disable-sync')
    if is_linux:
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
    if is_windows:
        chrome_options.add_argument('--disable-gpu')
    try:
        service = Service()
        service.log_path = 'NUL' if is_windows else '/dev/null'
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f" Failed to create Chrome driver: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure Google Chrome is installed")
        print("  2. Check that Chrome version matches ChromeDriver")
        if is_windows:
            print("  3. Download ChromeDriver from: https://chromedriver.chromium.org/")
        raise
def get_available_files():
    # Get list of files from the configured directory.
    files_dir = Path(PRODUCER_FILES_DIR)
    if not files_dir.exists():
        print(f" Files directory '{PRODUCER_FILES_DIR}' does not exist")
        return []
    files = [f for f in files_dir.iterdir() if f.is_file()]
    if not files:
        print(f" No files found in '{PRODUCER_FILES_DIR}'")
    return files
def upload_file_selenium(user_id, file_path, attempt=1):
    # Simulates real user behavior.
    driver = None
    try:
        driver = get_chrome_driver()
        print(f"[User {user_id}] Opening upload page: {PRODUCER_TARGET_BASE_URL}")
        driver.get(PRODUCER_TARGET_BASE_URL)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "form"))
        )
        file_input = driver.find_element(By.NAME, "file")
        absolute_path = str(file_path.resolve())
        if sys.platform.startswith('win'):
            absolute_path = absolute_path.replace('/', '\\')
        file_input.send_keys(absolute_path)
        print(f"[User {user_id}] Selected file: {file_path.name}")
        try:
            uploader_input = driver.find_element(By.NAME, "uploader_id")
            uploader_input.clear()
            uploader_input.send_keys(f"user_{user_id}")
        except:
            pass  
        # Small delay to simulate human behavior
        time.sleep(random.uniform(0.5, 1.5))
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
        submit_button.click()
        print(f"[User {user_id}] Submitted upload for: {file_path.name}")
        # Wait a moment to ensure submission completes
        time.sleep(2)
        return True
    except Exception as e:
        print(f" [User {user_id}] Upload failed (attempt {attempt}): {e}")
        return False  
    finally:
        if driver:
            driver.quit()
def user_upload_session(user_id, files, num_uploads):
    # Simulates a user session uploading multiple files.
    print(f" [User {user_id}] Starting session ({num_uploads} uploads)")
    successful_uploads = 0
    failed_uploads = 0
    for i in range(num_uploads):
        if not files:
            print(f" [User {user_id}] No files available to upload")
            break
        file_to_upload = random.choice(files)
        success = upload_file_selenium(user_id, file_to_upload)
        if success:
            successful_uploads += 1
        else:
            failed_uploads += 1
        if i < num_uploads - 1:
            delay = random.uniform(2, 5)
            print(f"[User {user_id}] Waiting {delay:.1f}s before next upload...")
            time.sleep(delay)
    print(f" [User {user_id}] Session complete: {successful_uploads} successful, {failed_uploads} failed")
    return {
        'user_id': user_id,
        'successful': successful_uploads,
        'failed': failed_uploads
    }
def run_producer():
    # Spawns multiple concurrent users uploading files.
    print(" ConnectStorm Selenium Producer")
    print(f"   Target URL: {PRODUCER_TARGET_BASE_URL}")
    print(f"   Files Directory: {PRODUCER_FILES_DIR}")
    print(f"   Concurrent Users: {PRODUCER_USERS}")
    print(f"   Uploads per User: {PRODUCER_REPEATS}")
    print(f"   Headless Mode: {PRODUCER_HEADLESS}")
    print()
    files = get_available_files()
    if not files:
        print(" No files found to upload. Please add files to the 'files/' directory.")
        return
    print(f" Found {len(files)} files to upload:")
    for f in files:
        print(f"  - {f.name} ({f.stat().st_size} bytes)")
    print()
    start_time = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=PRODUCER_USERS) as executor:
        futures = {
            executor.submit(user_upload_session, i+1, files, PRODUCER_REPEATS): i+1
            for i in range(PRODUCER_USERS)
        }
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f" User session error: {e}")
    elapsed_time = time.time() - start_time
    total_successful = sum(r['successful'] for r in results)
    total_failed = sum(r['failed'] for r in results)
    print()
    print("=" * 60)
    print("STRESS TEST SUMMARY")
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
        print("\n Producer interrupted by user")
    except Exception as e:
        print(f" Producer error: {e}")
        sys.exit(1)