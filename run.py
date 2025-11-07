#!/usr/bin/env python3
"""
File-Storm Multi-Process Runner
Runs all services in parallel using multiprocessing.
"""

import os
import sys
import time
import signal
import subprocess
from multiprocessing import Process

def run_service(name, command):
    """Run a service with the given command."""
    print(f"🚀 Starting {name}...")
    try:
        subprocess.run(command, shell=True)
    except KeyboardInterrupt:
        print(f"\n⚠ {name} interrupted")
    except Exception as e:
        print(f"✗ {name} error: {e}")

def main():
    print("⚡ File-Storm Multi-Service Runner")
    print("=" * 50)
    print()
    
    # Define services
    services = [
        ("Flask Web", "python app.py"),
        ("Consumer Worker", "python consumer.py"),
        # Uncomment to auto-start producer:
        # ("Selenium Producer", "python selenium_producer.py"),
    ]
    
    # Start all services as processes
    processes = []
    
    for name, command in services:
        p = Process(target=run_service, args=(name, command))
        p.start()
        processes.append(p)
        time.sleep(1)  # Stagger startup
    
    print()
    print("✓ All services started!")
    print("  - Web: http://localhost:8080")
    print("  - Upload: http://localhost:8080/upload")
    print("  - Dashboard: http://localhost:8080/dashboard")
    print()
    print("Press Ctrl+C to stop all services")
    print()
    
    try:
        # Wait for all processes
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("\n⚠ Shutting down all services...")
        for p in processes:
            p.terminate()
        for p in processes:
            p.join()
        print("✓ All services stopped")

if __name__ == '__main__':
    main()

