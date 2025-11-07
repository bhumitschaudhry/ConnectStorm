#!/usr/bin/env python3
import os
import sys
import redis
import psycopg2
from datetime import datetime, timezone
from dotenv import load_dotenv
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
STREAM_KEY = 'connectstorm:uploads'
CONSUMER_GROUP = 'connectstorm_group'
PG_URI = os.getenv('PG_URI', 'postgresql://postgres:postgres@localhost:5432/filestorm')
def format_bytes(bytes_value):
    if bytes_value is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"
def get_redis_stats():
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        stream_length = redis_client.xlen(STREAM_KEY)
        try:
            pending = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
            pending_count = pending['pending'] if pending else 0
        except:
            pending_count = 0
        
        return {
            'connected': True,
            'stream_length': stream_length,
            'pending_count': pending_count,
            'error': None
        }
    except Exception as e:
        return {
            'connected': False,
            'stream_length': 0,
            'pending_count': 0,
            'error': str(e)
        }
def get_timescale_stats():
    try:
        conn = psycopg2.connect(PG_URI)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM file_events")
        total_records = cur.fetchone()[0]
        cur.execute("SELECT SUM(file_size) FROM file_events")
        total_size = cur.fetchone()[0] or 0
        cur.execute("""
            SELECT operation, COUNT(*), SUM(file_size)
            FROM file_events
            GROUP BY operation
            ORDER BY COUNT(*) DESC
        """)
        by_operation = cur.fetchall()
        cur.execute("""
            SELECT COUNT(*)
            FROM file_events
            WHERE event_time > NOW() - INTERVAL '24 hours'
        """)
        last_24h = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*)
            FROM file_events
            WHERE event_time > NOW() - INTERVAL '1 hour'
        """)
        last_hour = cur.fetchone()[0]
        cur.execute("""
            SELECT uploader_id, COUNT(*) as upload_count
            FROM file_events
            GROUP BY uploader_id
            ORDER BY upload_count DESC
            LIMIT 5
        """)
        top_uploaders = cur.fetchall()
        cur.execute("""
            SELECT filename, file_size, event_time
            FROM file_events
            ORDER BY event_time DESC
            LIMIT 1
        """)
        latest = cur.fetchone()
        cur.close()
        conn.close()
        return {
            'connected': True,
            'total_records': total_records,
            'total_size': total_size,
            'by_operation': by_operation,
            'last_24h': last_24h,
            'last_hour': last_hour,
            'top_uploaders': top_uploaders,
            'latest': latest,
            'error': None
        }
    except Exception as e:
        return {
            'connected': False,
            'total_records': 0,
            'total_size': 0,
            'by_operation': [],
            'last_24h': 0,
            'last_hour': 0,
            'top_uploaders': [],
            'latest': None,
            'error': str(e)
        }
def print_status():
    print("=" * 70)
    print("CONNECTSTORM SYSTEM STATUS")
    print("=" * 70)
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print()
    print("-" * 70)
    print("REDIS STREAM (Message Queue)")
    print("-" * 70)
    redis_stats = get_redis_stats()
    if redis_stats['connected']:
        print(f"Status:           CONNECTED")
        print(f"Stream:           {STREAM_KEY}")
        print(f"Queue Length:     {redis_stats['stream_length']} messages")
        print(f"Pending:          {redis_stats['pending_count']} messages")
        if redis_stats['stream_length'] == 0:
            print("Queue Status:     EMPTY (ready for new uploads)")
        else:
            print(f"Queue Status:     {redis_stats['stream_length']} messages waiting to be processed")
    else:
        print(f"Status:           DISCONNECTED")
        print(f"Error:            {redis_stats['error']}")
    print()
    print("-" * 70)
    print("TIMESCALEDB (Permanent Storage)")
    print("-" * 70)
    ts_stats = get_timescale_stats()
    if ts_stats['connected']:
        print(f"Status:           CONNECTED")
        print(f"Total Records:    {ts_stats['total_records']:,}")
        print(f"Total Data Size:  {format_bytes(ts_stats['total_size'])}")
        print()
        if ts_stats['by_operation']:
            print("By Operation:")
            for op, count, size in ts_stats['by_operation']:
                print(f"  - {op:12} {count:6,} records  ({format_bytes(size)})")
            print()
        print("Recent Activity:")
        print(f"  - Last Hour:      {ts_stats['last_hour']:,} uploads")
        print(f"  - Last 24 Hours:  {ts_stats['last_24h']:,} uploads")
        print()
        if ts_stats['top_uploaders']:
            print("Top Uploaders:")
            for uploader, count in ts_stats['top_uploaders']:
                print(f"  - {uploader:20} {count:6,} uploads")
            print()
        if ts_stats['latest']:
            filename, size, event_time = ts_stats['latest']
            print("Latest Upload:")
            print(f"  - File:           {filename}")
            print(f"  - Size:           {format_bytes(size)}")
            print(f"  - Time:           {event_time}")
        else:
            print("Latest Upload:    No uploads yet")
    else:
        print(f"Status:           DISCONNECTED")
        print(f"Error:            {ts_stats['error']}")
    print()
    print("=" * 70)
    if redis_stats['connected'] and ts_stats['connected']:
        print("SYSTEM HEALTH:    HEALTHY")
        if redis_stats['stream_length'] > 100:
            print("WARNING:          High queue backlog - consumer may be slow")
    elif not redis_stats['connected'] and not ts_stats['connected']:
        print("SYSTEM HEALTH:    CRITICAL - Both services down")
    else:
        print("SYSTEM HEALTH:    DEGRADED - One service unavailable")
    print("=" * 70)
if __name__ == '__main__':
    try:
        print_status()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)