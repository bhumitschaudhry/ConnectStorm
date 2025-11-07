#!/usr/bin/env python3
"""
ConnectStorm Reset Script - Clear all data from Redis and TimescaleDB
WARNING: This will delete all uploaded file records and pending messages!
"""
import os
import sys
import redis
import psycopg2
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
STREAM_KEY = 'connectstorm:uploads'
CONSUMER_GROUP = 'connectstorm_group'
PG_URI = os.getenv('PG_URI', 'postgresql://postgres:postgres@localhost:5432/filestorm')


def get_current_counts():
    """Get current data counts before reset."""
    counts = {
        'redis_stream': 0,
        'redis_pending': 0,
        'timescale_records': 0,
        'redis_error': None,
        'timescale_error': None
    }
    
    # Redis counts
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        counts['redis_stream'] = redis_client.xlen(STREAM_KEY)
        
        try:
            pending = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
            counts['redis_pending'] = pending['pending'] if pending else 0
        except:
            counts['redis_pending'] = 0
    except Exception as e:
        counts['redis_error'] = str(e)
    
    # TimescaleDB counts
    try:
        conn = psycopg2.connect(PG_URI)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM file_events")
        counts['timescale_records'] = cur.fetchone()[0]
        cur.close()
        conn.close()
    except Exception as e:
        counts['timescale_error'] = str(e)
    
    return counts


def reset_redis():
    """Clear all messages from Redis stream."""
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Get current count
        before_count = redis_client.xlen(STREAM_KEY)
        
        if before_count > 0:
            print(f"  Deleting {before_count} messages from Redis stream...")
            
            # Delete the entire stream
            redis_client.delete(STREAM_KEY)
            
            # Recreate the consumer group
            try:
                redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
                print(f"  Recreated consumer group '{CONSUMER_GROUP}'")
            except redis.exceptions.ResponseError as e:
                if 'BUSYGROUP' not in str(e):
                    print(f"  Warning: Could not recreate consumer group: {e}")
            
            print(f"  ✓ Redis stream cleared successfully")
        else:
            print(f"  Redis stream already empty (0 messages)")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Redis reset failed: {e}")
        return False


def reset_timescale():
    """Delete all records from TimescaleDB file_events table."""
    try:
        conn = psycopg2.connect(PG_URI)
        cur = conn.cursor()
        
        # Get current count
        cur.execute("SELECT COUNT(*) FROM file_events")
        before_count = cur.fetchone()[0]
        
        if before_count > 0:
            print(f"  Deleting {before_count} records from TimescaleDB...")
            
            # Delete all records
            cur.execute("DELETE FROM file_events")
            deleted = cur.rowcount
            
            conn.commit()
            print(f"  ✓ TimescaleDB cleared: {deleted} records deleted")
        else:
            print(f"  TimescaleDB already empty (0 records)")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ✗ TimescaleDB reset failed: {e}")
        return False


def main():
    """Main reset function."""
    print("=" * 70)
    print("CONNECTSTORM RESET SCRIPT")
    print("=" * 70)
    print()
    print("⚠️  WARNING: This will permanently delete:")
    print("   - All messages from Redis stream")
    print("   - All records from TimescaleDB")
    print()
    
    # Get current counts
    print("Checking current data...")
    counts = get_current_counts()
    
    print()
    print("-" * 70)
    print("CURRENT DATA:")
    print("-" * 70)
    
    if counts['redis_error']:
        print(f"Redis:       ERROR - {counts['redis_error']}")
    else:
        print(f"Redis Stream:    {counts['redis_stream']} messages")
        print(f"Redis Pending:   {counts['redis_pending']} pending")
    
    if counts['timescale_error']:
        print(f"TimescaleDB:     ERROR - {counts['timescale_error']}")
    else:
        print(f"TimescaleDB:     {counts['timescale_records']} records")
    
    print("-" * 70)
    print()
    
    # Check if there's anything to delete
    total_items = counts['redis_stream'] + counts['timescale_records']
    
    if total_items == 0:
        print("✓ All systems are already empty. Nothing to reset.")
        return
    
    # Confirmation
    print(f"Total items to delete: {total_items}")
    print()
    confirm = input("Type 'RESET' to confirm deletion: ")
    
    if confirm != 'RESET':
        print("\n❌ Reset cancelled.")
        return
    
    print()
    print("=" * 70)
    print("RESETTING SYSTEMS...")
    print("=" * 70)
    print()
    
    # Reset Redis
    print("1. Resetting Redis Stream...")
    redis_success = reset_redis()
    print()
    
    # Reset TimescaleDB
    print("2. Resetting TimescaleDB...")
    timescale_success = reset_timescale()
    print()
    
    # Final verification
    print("=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    
    final_counts = get_current_counts()
    
    print()
    if final_counts['redis_error']:
        print(f"Redis:       ERROR - {final_counts['redis_error']}")
    else:
        print(f"Redis Stream:    {final_counts['redis_stream']} messages")
    
    if final_counts['timescale_error']:
        print(f"TimescaleDB:     ERROR - {final_counts['timescale_error']}")
    else:
        print(f"TimescaleDB:     {final_counts['timescale_records']} records")
    
    print()
    
    if redis_success and timescale_success:
        if final_counts['redis_stream'] == 0 and final_counts['timescale_records'] == 0:
            print("✓ SUCCESS: All systems reset successfully!")
            print()
            print("You can now:")
            print("  1. Start fresh with new uploads")
            print("  2. Run: python app.py")
            print("  3. Run: python consumer.py")
            print("  4. Upload files via http://localhost:8080/upload")
        else:
            print("⚠️  WARNING: Systems not completely empty after reset")
    else:
        print("❌ ERROR: Reset incomplete. Check error messages above.")
    
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Reset cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

