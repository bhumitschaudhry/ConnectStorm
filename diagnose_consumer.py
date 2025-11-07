#!/usr/bin/env python3
"""
Diagnose why consumer isn't processing messages
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

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
STREAM_KEY = 'connectstorm:uploads'
CONSUMER_GROUP = 'connectstorm_group'
PG_URI = os.getenv('PG_URI', 'postgresql://postgres:postgres@localhost:5432/filestorm')
ENABLE_CONSUMER = os.getenv('ENABLE_CONSUMER', 'true').lower() == 'true'

print("=" * 70)
print("CONSUMER DIAGNOSTIC")
print("=" * 70)
print()

# Check 1: Environment variable
print("1. CHECKING ENABLE_CONSUMER")
print("-" * 70)
print(f"ENABLE_CONSUMER env var: {os.getenv('ENABLE_CONSUMER', 'NOT SET')}")
print(f"ENABLE_CONSUMER parsed: {ENABLE_CONSUMER}")
if not ENABLE_CONSUMER:
    print("❌ PROBLEM: ENABLE_CONSUMER is not 'true'")
    print("   Fix: Set ENABLE_CONSUMER=true in .env or Render dashboard")
else:
    print("✅ ENABLE_CONSUMER is set correctly")
print()

# Check 2: Redis connection
print("2. CHECKING REDIS")
print("-" * 70)
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("✅ Redis connection: OK")
    
    # Check stream
    stream_len = redis_client.xlen(STREAM_KEY)
    print(f"✅ Stream '{STREAM_KEY}': {stream_len} messages")
    
    if stream_len > 0:
        print(f"⚠️  {stream_len} messages waiting to be processed")
        
        # Check consumer group
        try:
            # Try to read with consumer group
            messages = redis_client.xreadgroup(
                CONSUMER_GROUP,
                'diagnostic_consumer',
                {STREAM_KEY: '>'},
                count=1,
                block=100
            )
            if messages:
                print("✅ Consumer group can read messages")
                for stream, msgs in messages:
                    for msg_id, msg_data in msgs:
                        print(f"   Sample message: {msg_id}")
                        print(f"   Data: {list(msg_data.keys())}")
            else:
                print("⚠️  No messages returned from consumer group")
        except redis.exceptions.ResponseError as e:
            if 'NOGROUP' in str(e):
                print("❌ PROBLEM: Consumer group doesn't exist!")
                print(f"   Error: {e}")
                print("   Fix: Consumer needs to initialize the group")
            else:
                print(f"❌ Error reading from consumer group: {e}")
    else:
        print("✅ No messages in queue (expected if all processed)")
        
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
print()

# Check 3: Database connection
print("3. CHECKING TIMESCALEDB")
print("-" * 70)
try:
    conn = psycopg2.connect(PG_URI)
    cur = conn.cursor()
    
    # Check table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'file_events'
        )
    """)
    table_exists = cur.fetchone()[0]
    
    if table_exists:
        print("✅ Table 'file_events' exists")
        
        # Check record count
        cur.execute("SELECT COUNT(*) FROM file_events")
        count = cur.fetchone()[0]
        print(f"✅ Records in database: {count}")
        
        if count == 0 and stream_len > 0:
            print("❌ PROBLEM: Messages in Redis but no records in DB!")
            print("   This means consumer is not processing messages")
    else:
        print("❌ PROBLEM: Table 'file_events' doesn't exist!")
        print("   Fix: Run schema.sql to create the table")
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Database connection failed: {e}")
    print("   Check PG_URI environment variable")
print()

# Check 4: Pending messages
print("4. CHECKING PENDING MESSAGES")
print("-" * 70)
try:
    pending = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
    if pending:
        pending_count = pending['pending']
        print(f"⚠️  {pending_count} messages pending (in progress but not acknowledged)")
        if pending_count > 0:
            print("   These messages might be stuck!")
            # Show details
            pending_details = redis_client.xpending_range(
                STREAM_KEY, CONSUMER_GROUP, min='-', max='+', count=5
            )
            for p in pending_details:
                print(f"   - Message ID: {p['message_id']}")
                print(f"     Consumer: {p['consumer']}")
                print(f"     Idle time: {p['time_since_delivered']}ms")
except Exception as e:
    if 'NOGROUP' in str(e):
        print("⚠️  Consumer group doesn't exist (will be created on first use)")
    else:
        print(f"⚠️  Could not check pending: {e}")
print()

# Summary
print("=" * 70)
print("DIAGNOSIS SUMMARY")
print("=" * 70)
print()

issues = []

if not ENABLE_CONSUMER:
    issues.append("ENABLE_CONSUMER is not set to 'true'")

if stream_len > 0:
    issues.append(f"{stream_len} messages stuck in Redis queue")

print("POSSIBLE ISSUES:")
if issues:
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue}")
else:
    print("✅ No obvious issues found")

print()
print("RECOMMENDED FIXES:")
print("1. Set ENABLE_CONSUMER=true in Render dashboard")
print("2. Check Render logs for consumer errors")
print("3. Verify database connection (PG_URI)")
print("4. Check if consumer thread started (look for 'Consumer worker started')")
print()
print("=" * 70)

