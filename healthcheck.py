#!/usr/bin/env python3
"""
ConnectStorm Health Check Script
Verifies all external dependencies and configuration.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

def check_env_var(name, required=True):
    """Check if environment variable is set."""
    value = os.getenv(name)
    if value:
        # Mask sensitive values
        if any(k in name.lower() for k in ['key', 'secret', 'password', 'uri', 'url']):
            display = value[:8] + '...' if len(value) > 8 else '***'
        else:
            display = value
        print(f"  ✓ {name}: {display}")
        return True
    else:
        status = "✗" if required else "⚠"
        print(f"  {status} {name}: Not set")
        return not required

def check_redis():
    """Check Redis connection."""
    try:
        import redis
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            print("  ✗ REDIS_URL not set")
            return False
        
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        print("  ✓ Redis connection successful")
        
        # Check stream
        stream_len = client.xlen('filestorm:uploads')
        print(f"  ✓ Redis stream length: {stream_len}")
        
        return True
    except ImportError:
        print("  ✗ redis package not installed")
        return False
    except Exception as e:
        print(f"  ✗ Redis connection failed: {e}")
        return False

def check_database():
    """Check PostgreSQL/TimescaleDB connection."""
    try:
        import psycopg2
        pg_uri = os.getenv('PG_URI')
        if not pg_uri:
            print("  ✗ PG_URI not set")
            return False
        
        conn = psycopg2.connect(pg_uri)
        cur = conn.cursor()
        
        # Check connection
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"  ✓ PostgreSQL connection successful")
        print(f"    Version: {version[:50]}...")
        
        # Check TimescaleDB extension
        cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname='timescaledb';")
        result = cur.fetchone()
        if result:
            print(f"  ✓ TimescaleDB extension: v{result[1]}")
        else:
            print("  ⚠ TimescaleDB extension not found")
        
        # Check table exists
        cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='file_events');")
        table_exists = cur.fetchone()[0]
        if table_exists:
            cur.execute("SELECT COUNT(*) FROM file_events;")
            count = cur.fetchone()[0]
            print(f"  ✓ file_events table exists ({count} records)")
        else:
            print("  ⚠ file_events table not found - run schema.sql")
        
        cur.close()
        conn.close()
        return True
        
    except ImportError:
        print("  ✗ psycopg2 package not installed")
        return False
    except Exception as e:
        print(f"  ✗ Database connection failed: {e}")
        return False

def check_storage():
    """Check storage configuration."""
    storage_mode = os.getenv('STORAGE_MODE', 'local')
    print(f"  ✓ Storage mode: {storage_mode}")
    
    if storage_mode == 's3':
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            s3_bucket = os.getenv('S3_BUCKET')
            s3_access_key = os.getenv('S3_ACCESS_KEY')
            s3_secret_key = os.getenv('S3_SECRET_KEY')
            
            if not all([s3_bucket, s3_access_key, s3_secret_key]):
                print("  ✗ S3 credentials incomplete")
                return False
            
            # Try to connect
            s3_endpoint = os.getenv('S3_ENDPOINT')
            s3_region = os.getenv('S3_REGION', 'us-east-1')
            
            if s3_endpoint:
                client = boto3.client(
                    's3',
                    endpoint_url=s3_endpoint,
                    aws_access_key_id=s3_access_key,
                    aws_secret_access_key=s3_secret_key,
                    region_name=s3_region
                )
            else:
                client = boto3.client(
                    's3',
                    aws_access_key_id=s3_access_key,
                    aws_secret_access_key=s3_secret_key,
                    region_name=s3_region
                )
            
            # Check bucket access
            client.head_bucket(Bucket=s3_bucket)
            print(f"  ✓ S3 bucket '{s3_bucket}' accessible")
            return True
            
        except ImportError:
            print("  ✗ boto3 package not installed")
            return False
        except ClientError as e:
            print(f"  ✗ S3 access failed: {e}")
            return False
        except Exception as e:
            print(f"  ✗ S3 configuration error: {e}")
            return False
    else:
        local_dir = os.getenv('LOCAL_STORAGE_DIR', '/tmp/filestorm_storage')
        print(f"  ✓ Local storage directory: {local_dir}")
        return True

def check_selenium():
    """Check Selenium configuration."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        print("  ✓ Selenium package installed")
        
        # Check files directory
        files_dir = os.getenv('PRODUCER_FILES_DIR', 'files')
        if os.path.exists(files_dir):
            files = [f for f in os.listdir(files_dir) if os.path.isfile(os.path.join(files_dir, f))]
            print(f"  ✓ Files directory exists ({len(files)} files)")
        else:
            print(f"  ⚠ Files directory '{files_dir}' not found")
        
        return True
        
    except ImportError:
        print("  ✗ selenium package not installed")
        return False
    except Exception as e:
        print(f"  ✗ Selenium check failed: {e}")
        return False

def main():
    """Run all health checks."""
    print("⚡ ConnectStorm Health Check")
    print("=" * 60)
    print()
    
    # Track results
    results = {}
    
    # 1. Check Python packages
    print("📦 Checking Python Packages:")
    try:
        import flask
        print(f"  ✓ Flask: {flask.__version__}")
    except ImportError:
        print("  ✗ Flask not installed")
    
    try:
        import redis
        print(f"  ✓ redis: {redis.__version__}")
    except ImportError:
        print("  ✗ redis not installed")
    
    try:
        import psycopg2
        print(f"  ✓ psycopg2: {psycopg2.__version__}")
    except ImportError:
        print("  ✗ psycopg2 not installed")
    
    try:
        import boto3
        print(f"  ✓ boto3: {boto3.__version__}")
    except ImportError:
        print("  ✗ boto3 not installed")
    
    try:
        from selenium import webdriver
        print("  ✓ selenium installed")
    except ImportError:
        print("  ✗ selenium not installed")
    
    print()
    
    # 2. Check environment variables
    print("🔧 Checking Environment Variables:")
    check_env_var('FLASK_PORT', required=False)
    check_env_var('SECRET_KEY')
    check_env_var('REDIS_URL')
    check_env_var('PG_URI')
    check_env_var('STORAGE_MODE', required=False)
    
    storage_mode = os.getenv('STORAGE_MODE', 'local')
    if storage_mode == 's3':
        check_env_var('S3_BUCKET')
        check_env_var('S3_ACCESS_KEY')
        check_env_var('S3_SECRET_KEY')
    
    print()
    
    # 3. Check Redis
    print("🔴 Checking Redis:")
    results['redis'] = check_redis()
    print()
    
    # 4. Check Database
    print("🐘 Checking PostgreSQL/TimescaleDB:")
    results['database'] = check_database()
    print()
    
    # 5. Check Storage
    print("💾 Checking Storage:")
    results['storage'] = check_storage()
    print()
    
    # 6. Check Selenium
    print("🤖 Checking Selenium:")
    results['selenium'] = check_selenium()
    print()
    
    # Summary
    print("=" * 60)
    print("📊 HEALTH CHECK SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for component, status in results.items():
        icon = "✓" if status else "✗"
        print(f"  {icon} {component.capitalize()}: {'PASS' if status else 'FAIL'}")
    
    print()
    
    if all_passed:
        print("✅ All checks passed! System is ready to run.")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())

