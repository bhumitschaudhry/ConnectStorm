#!/usr/bin/env python3
"""
File-Storm Consumer Worker
Reads from Redis Stream, uploads to S3/R2, and inserts into TimescaleDB.
"""

import os
import sys
import time
import json
from datetime import datetime
import redis
import psycopg2
from dotenv import load_dotenv
from storage import upload_file

load_dotenv()

# Redis configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
STREAM_KEY = 'filestorm:uploads'
CONSUMER_GROUP = 'filestorm_group'
CONSUMER_NAME = os.getenv('CONSUMER_NAME', f'consumer_{os.getpid()}')

# PostgreSQL/TimescaleDB configuration
PG_URI = os.getenv('PG_URI', 'postgresql://postgres:postgres@localhost:5432/filestorm')

# Batch configuration
BATCH_SIZE = int(os.getenv('CONSUMER_BATCH_SIZE', '10'))
BLOCK_MS = int(os.getenv('CONSUMER_BLOCK_MS', '5000'))  # 5 seconds

# Redis client
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(PG_URI)


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
    Process a single message:
    1. Upload file to S3/R2
    2. Insert metadata into TimescaleDB
    3. Return success status
    """
    try:
        # Extract message fields
        operation = message_data.get('operation', 'UPLOAD')
        filename = message_data.get('filename')
        size = int(message_data.get('size', 0))
        mime_type = message_data.get('mime_type', 'application/octet-stream')
        tmp_path = message_data.get('tmp_path')
        uploader_id = message_data.get('uploader_id', 'anonymous')
        ts = message_data.get('ts', datetime.utcnow().isoformat() + 'Z')
        
        if not tmp_path or not os.path.exists(tmp_path):
            print(f"⚠ File not found: {tmp_path}")
            return False
        
        # Upload file to S3/R2/local storage
        storage_url = upload_file(tmp_path, filename)
        
        # Insert into TimescaleDB
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO file_events (
                event_time, operation, filename, file_size, 
                mime_type, storage_url, uploader_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            ts,
            operation,
            filename,
            size,
            mime_type,
            storage_url,
            uploader_id
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Clean up temporary file
        try:
            os.remove(tmp_path)
        except Exception as e:
            print(f"⚠ Failed to delete temp file {tmp_path}: {e}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error processing message: {e}")
        return False


def consume_batch():
    """
    Read a batch of messages from Redis Stream and process them.
    """
    try:
        # Read messages from stream
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
        
        # Process each stream
        for stream_name, stream_messages in messages:
            for message_id, message_data in stream_messages:
                print(f"📥 Processing message {message_id}")
                
                # Process the message
                success = process_message(message_data)
                
                if success:
                    # Acknowledge and delete message
                    redis_client.xack(STREAM_KEY, CONSUMER_GROUP, message_id)
                    redis_client.xdel(STREAM_KEY, message_id)
                    processed_count += 1
                    print(f"✓ Processed and acknowledged {message_id}")
                else:
                    print(f"✗ Failed to process {message_id}, will retry later")
        
        if processed_count > 0:
            print(f"✓ Batch complete: {processed_count} messages processed")
        
        return processed_count
        
    except Exception as e:
        print(f"✗ Error in consume_batch: {e}")
        return 0


def run_consumer():
    """
    Main consumer loop.
    """
    print(f"🚀 Starting File-Storm Consumer Worker")
    print(f"   Consumer Name: {CONSUMER_NAME}")
    print(f"   Stream Key: {STREAM_KEY}")
    print(f"   Consumer Group: {CONSUMER_GROUP}")
    print(f"   Batch Size: {BATCH_SIZE}")
    print(f"   Block Time: {BLOCK_MS}ms")
    print()
    
    # Initialize consumer group
    init_consumer_group()
    
    # Main loop
    total_processed = 0
    
    while True:
        try:
            count = consume_batch()
            total_processed += count
            
            if count > 0:
                print(f"📊 Total processed: {total_processed}")
            
        except KeyboardInterrupt:
            print(f"\n⚠ Shutting down consumer... Total processed: {total_processed}")
            break
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            time.sleep(5)  # Wait before retry


if __name__ == '__main__':
    run_consumer()

