#!/usr/bin/env python3
"""
ConnectStorm Consumer Worker (CLOUD VERSION)
Works with distributed deployment where app and consumer are on different machines.
Files are already in S3/R2 when consumer receives the message.
"""

import os
import sys
import time
from datetime import datetime, timezone
import redis
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

load_dotenv()

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
STREAM_KEY = 'connectstorm:uploads'
CONSUMER_GROUP = 'connectstorm_group'
CONSUMER_NAME = os.getenv('CONSUMER_NAME', f'consumer_{os.getpid()}')

# PostgreSQL/TimescaleDB configuration
PG_URI = os.getenv('PG_URI', 'postgresql://postgres:postgres@localhost:5432/filestorm')

# Batch configuration
BATCH_SIZE = int(os.getenv('CONSUMER_BATCH_SIZE', '50'))
BLOCK_MS = int(os.getenv('CONSUMER_BLOCK_MS', '1000'))

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Database connection pool
db_pool = None


def init_db_pool():
    """Initialize database connection pool."""
    global db_pool
    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=PG_URI
        )
        print(f"✓ Database connection pool initialized")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize connection pool: {e}")
        return False


def get_db_connection():
    """Get connection from pool."""
    if db_pool:
        return db_pool.getconn()
    else:
        return psycopg2.connect(PG_URI)


def return_db_connection(conn):
    """Return connection to pool."""
    if db_pool:
        db_pool.putconn(conn)
    else:
        conn.close()


def init_consumer_group():
    """Initialize Redis consumer group if not exists."""
    try:
        redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
        print(f"✓ Created consumer group '{CONSUMER_GROUP}'")
    except redis.exceptions.ResponseError as e:
        if 'BUSYGROUP' in str(e):
            print(f"✓ Consumer group '{CONSUMER_GROUP}' already exists")
        else:
            raise


def process_message(message_data):
    """
    Process a single message (CLOUD VERSION).
    File is already in S3/R2, just insert metadata to database.
    """
    try:
        # Extract message fields
        operation = message_data.get('operation', 'UPLOAD')
        filename = message_data.get('filename')
        size = int(message_data.get('size', 0))
        mime_type = message_data.get('mime_type', 'application/octet-stream')
        storage_url = message_data.get('storage_url')
        uploader_id = message_data.get('uploader_id', 'anonymous')
        ts = message_data.get('ts', datetime.now(timezone.utc).isoformat())
        already_stored = message_data.get('already_stored', 'false')
        
        # Check if this is cloud mode (file already stored)
        if already_stored == 'true':
            # File is already in S3/R2, just return metadata for DB insert
            if not storage_url:
                print(f"⚠ No storage URL provided")
                return 'skip', None
            
            metadata = {
                'event_time': ts,
                'operation': operation,
                'filename': filename,
                'file_size': size,
                'mime_type': mime_type,
                'storage_url': storage_url,
                'uploader_id': uploader_id
            }
            
            return 'success', metadata
        
        else:
            # Legacy mode: file path provided (for backwards compatibility)
            tmp_path = message_data.get('tmp_path')
            
            if not tmp_path or not os.path.exists(tmp_path):
                print(f"⚠ File not found: {tmp_path} - skipping")
                return 'skip', None
            
            # Upload file to storage (old flow)
            from storage import upload_file
            storage_url = upload_file(tmp_path, filename)
            
            # Clean up temp file
            try:
                os.remove(tmp_path)
            except Exception as e:
                print(f"⚠ Failed to delete temp file: {e}")
            
            metadata = {
                'event_time': ts,
                'operation': operation,
                'filename': filename,
                'file_size': size,
                'mime_type': mime_type,
                'storage_url': storage_url,
                'uploader_id': uploader_id
            }
            
            return 'success', metadata
        
    except Exception as e:
        print(f"✗ Error processing message: {e}")
        return 'error', None


def batch_insert_to_db(records):
    """Insert multiple records to database in a single transaction."""
    if not records:
        return 0
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO file_events (
                event_time, operation, filename, file_size, 
                mime_type, storage_url, uploader_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        data_tuples = [
            (
                record['event_time'],
                record['operation'],
                record['filename'],
                record['file_size'],
                record['mime_type'],
                record['storage_url'],
                record['uploader_id']
            )
            for record in records
        ]
        
        cur.executemany(insert_query, data_tuples)
        conn.commit()
        
        inserted_count = cur.rowcount
        cur.close()
        return_db_connection(conn)
        
        return inserted_count
        
    except Exception as e:
        print(f"✗ Batch insert error: {e}")
        if conn:
            conn.rollback()
            return_db_connection(conn)
        return 0


def consume_batch():
    """Read and process a batch of messages from Redis Stream."""
    try:
        messages = redis_client.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            {STREAM_KEY: '>'},
            count=BATCH_SIZE,
            block=BLOCK_MS
        )
        
        if not messages:
            return 0
        
        processed_count = 0
        successful_records = []
        message_ids_to_ack = []
        message_ids_to_skip = []
        
        for stream_name, stream_messages in messages:
            for message_id, message_data in stream_messages:
                status, metadata = process_message(message_data)
                
                if status == 'success':
                    successful_records.append(metadata)
                    message_ids_to_ack.append(message_id)
                elif status == 'skip':
                    message_ids_to_skip.append(message_id)
        
        # Batch insert all successful records
        if successful_records:
            inserted = batch_insert_to_db(successful_records)
            
            if inserted > 0:
                for msg_id in message_ids_to_ack:
                    redis_client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                    redis_client.xdel(STREAM_KEY, msg_id)
                
                processed_count = inserted
                print(f"✓ Batch: {processed_count} records inserted")
        
        # Acknowledge skipped messages
        for msg_id in message_ids_to_skip:
            redis_client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
            redis_client.xdel(STREAM_KEY, msg_id)
        
        return processed_count
        
    except Exception as e:
        print(f"✗ Error in consume_batch: {e}")
        return 0


def run_consumer():
    """Main consumer loop."""
    print(f"🚀 ConnectStorm Consumer (CLOUD VERSION)")
    print(f"   Consumer: {CONSUMER_NAME}")
    print(f"   Stream: {STREAM_KEY}")
    print(f"   Group: {CONSUMER_GROUP}")
    print(f"   Batch Size: {BATCH_SIZE}")
    print(f"   Block Time: {BLOCK_MS}ms")
    print()
    
    if not init_db_pool():
        print("✗ Failed to initialize database pool")
        return
    
    init_consumer_group()
    
    print(f"👂 Listening for messages...")
    print(f"⚡ Optimized for distributed deployment (files in S3/R2)")
    print()
    
    total_processed = 0
    idle_cycles = 0
    start_time = time.time()
    
    while True:
        try:
            count = consume_batch()
            total_processed += count
            
            if count > 0:
                elapsed = time.time() - start_time
                rate = total_processed / elapsed if elapsed > 0 else 0
                print(f"📊 Total: {total_processed} | Rate: {rate:.2f}/sec")
                idle_cycles = 0
            else:
                idle_cycles += 1
                if idle_cycles % 60 == 0:
                    print(f"💓 Listening... (~{idle_cycles * BLOCK_MS // 1000}s idle)")
            
        except KeyboardInterrupt:
            print(f"\n⚠ Shutting down... Total: {total_processed}")
            break
        except Exception as e:
            print(f"✗ Error: {e}")
            time.sleep(5)
    
    if db_pool:
        db_pool.closeall()


if __name__ == '__main__':
    run_consumer()

