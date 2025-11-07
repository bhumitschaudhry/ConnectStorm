#!/usr/bin/env python3
"""
ConnectStorm Flask Application + Consumer (COMBINED)
Runs Flask web server + consumer worker in single process for Render free tier.
"""

import os
import json
import time
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import redis
import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv
from storage import upload_file

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Temporary directory for uploads
upload_folder = os.getenv('UPLOAD_FOLDER')
if upload_folder:
    app.config['UPLOAD_FOLDER'] = upload_folder
else:
    app.config['UPLOAD_FOLDER'] = os.path.join(tempfile.gettempdir(), 'connectstorm_uploads')

Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
print(f"Upload folder: {app.config['UPLOAD_FOLDER']}")

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Redis Stream configuration
STREAM_KEY = 'connectstorm:uploads'
CONSUMER_GROUP = 'connectstorm_group'
CONSUMER_NAME = os.getenv('CONSUMER_NAME', f'consumer_{os.getpid()}')

# PostgreSQL/TimescaleDB connection
PG_URI = os.getenv('PG_URI', 'postgresql://postgres:postgres@localhost:5432/filestorm')

# Storage mode
STORAGE_MODE = os.getenv('STORAGE_MODE', 'local')

# Consumer configuration
BATCH_SIZE = int(os.getenv('CONSUMER_BATCH_SIZE', '50'))
BLOCK_MS = int(os.getenv('CONSUMER_BLOCK_MS', '500'))  # Reduced to 500ms for faster processing
ENABLE_CONSUMER = os.getenv('ENABLE_CONSUMER', 'true').lower() == 'true'

# Database connection pool
db_pool = None
consumer_thread = None
consumer_running = False


# ============================================================================
# DATABASE SETUP
# ============================================================================

def init_db_pool():
    """Initialize database connection pool."""
    global db_pool
    try:
        db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=PG_URI
        )
        # Test connection
        test_conn = db_pool.getconn()
        test_cur = test_conn.cursor()
        test_cur.execute("SELECT 1")
        test_cur.close()
        db_pool.putconn(test_conn)
        print(f"Database connection pool initialized and tested")
        return True
    except Exception as e:
        print(f"Failed to initialize connection pool: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        print(f"   Check PG_URI: {PG_URI[:50]}..." if len(PG_URI) > 50 else f"   Check PG_URI: {PG_URI}")
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


def init_redis_stream():
    """Initialize Redis Stream and consumer group if not exists."""
    try:
        redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
        print(f"Created consumer group '{CONSUMER_GROUP}' for stream '{STREAM_KEY}'")
    except redis.exceptions.ResponseError as e:
        if 'BUSYGROUP' in str(e):
            print(f"Consumer group '{CONSUMER_GROUP}' already exists")
        else:
            print(f"Redis error creating consumer group: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")


# ============================================================================
# CONSUMER FUNCTIONS (Background Worker)
# ============================================================================

def process_message(message_data, message_id=None):
    """Process a single message."""
    try:
        operation = message_data.get('operation', 'UPLOAD')
        filename = message_data.get('filename')
        size = int(message_data.get('size', 0))
        mime_type = message_data.get('mime_type', 'application/octet-stream')
        storage_url = message_data.get('storage_url')
        uploader_id = message_data.get('uploader_id', 'anonymous')
        ts = message_data.get('ts', datetime.now(timezone.utc).isoformat())
        already_stored = message_data.get('already_stored', 'false')
        
        # Cloud mode: file already in S3/R2
        if already_stored == 'true':
            if not storage_url:
                return 'skip', None
            
            metadata = {
                'event_time': ts,
                'operation': operation,
                'filename': filename,
                'file_size': size,
                'mime_type': mime_type,
                'storage_url': storage_url,
                'uploader_id': uploader_id,
                'redis_message_id': message_id  # Store Redis message ID for deduplication
            }
            return 'success', metadata
        
        # Legacy mode: file path provided
        else:
            tmp_path = message_data.get('tmp_path')
            if not tmp_path or not os.path.exists(tmp_path):
                return 'skip', None
            
            storage_url = upload_file(tmp_path, filename)
            
            try:
                os.remove(tmp_path)
            except:
                pass
            
            metadata = {
                'event_time': ts,
                'operation': operation,
                'filename': filename,
                'file_size': size,
                'mime_type': mime_type,
                'storage_url': storage_url,
                'uploader_id': uploader_id,
                'redis_message_id': message_id  # Store Redis message ID for deduplication
            }
            return 'success', metadata
        
    except Exception as e:
        print(f"Error processing message: {e}")
        return 'error', None


def batch_insert_to_db(records):
    """Insert multiple records to database."""
    if not records:
        return 0
    
    if not db_pool:
        print("ERROR: Database pool not initialized, cannot insert records")
        return 0
    
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            print("ERROR: Failed to get database connection from pool")
            return 0
        
        cur = conn.cursor()
        
        # First, check which records already exist (application-level duplicate check)
        # This helps even if the unique index doesn't exist yet
        message_ids = [r.get('redis_message_id') for r in records if r.get('redis_message_id')]
        existing_ids = set()
        
        if message_ids:
            try:
                # Check which message IDs already exist in the database
                placeholders = ','.join(['%s'] * len(message_ids))
                check_query = f"""
                    SELECT redis_message_id 
                    FROM file_events 
                    WHERE redis_message_id IN ({placeholders})
                """
                cur.execute(check_query, message_ids)
                existing_ids = {row[0] for row in cur.fetchall() if row[0]}
            except Exception as check_error:
                # If column doesn't exist yet, or other error, just continue
                print(f"Note: Could not check for existing records: {check_error}")
                existing_ids = set()
        
        # Filter out records that already exist
        new_records = [
            r for r in records 
            if not r.get('redis_message_id') or r.get('redis_message_id') not in existing_ids
        ]
        
        if not new_records:
            print(f"All {len(records)} records already exist in database (duplicates skipped)")
            cur.close()
            return_db_connection(conn)
            return len(records)  # Return count as if inserted (they're already there)
        
        data_tuples = [
            (r['event_time'], r['operation'], r['filename'], 
             r['file_size'], r['mime_type'], r['storage_url'], r['uploader_id'], r.get('redis_message_id'))
            for r in new_records
        ]
        
        print(f"Batch insert: Attempting to insert {len(data_tuples)} new records (skipped {len(records) - len(new_records)} duplicates)...")
        
        # Try with ON CONFLICT first (if index exists), otherwise fall back to simple insert
        # Use ON CONFLICT to prevent duplicate inserts based on Redis message ID
        # This prevents the same Redis message from being processed multiple times
        # Note: TimescaleDB requires event_time in unique indexes, so we use (redis_message_id, event_time)
        try:
            insert_query_with_conflict = """
                INSERT INTO file_events (
                    event_time, operation, filename, file_size, 
                    mime_type, storage_url, uploader_id, redis_message_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (redis_message_id, event_time) DO NOTHING
            """
            cur.executemany(insert_query_with_conflict, data_tuples)
        except (psycopg2.errors.InvalidColumnReference, psycopg2.errors.UndefinedTable) as e:
            # Index doesn't exist yet, use simple insert (we already filtered duplicates at app level)
            print(f"Unique index not found ({type(e).__name__}), using simple insert (duplicates already filtered)")
            insert_query_simple = """
                INSERT INTO file_events (
                    event_time, operation, filename, file_size, 
                    mime_type, storage_url, uploader_id, redis_message_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cur.executemany(insert_query_simple, data_tuples)
        
        conn.commit()
        
        inserted_count = cur.rowcount
        cur.close()
        return_db_connection(conn)
        
        if inserted_count > 0:
            print(f"✓ Batch insert SUCCESS: {inserted_count} records inserted to database")
        else:
            print(f"WARNING: Batch insert returned 0 rows inserted (expected {len(data_tuples)})")
        
        return inserted_count
        
    except psycopg2.OperationalError as e:
        import traceback
        print(f"Batch insert database connection error: {e}")
        print(f"   This might indicate database is down or connection lost")
        if conn:
            try:
                conn.rollback()
                return_db_connection(conn)
            except:
                pass
        # Try to reinitialize connection pool
        try:
            init_db_pool()  # init_db_pool already handles global db_pool internally
        except:
            pass
        return 0
    except Exception as e:
        import traceback
        print(f"Batch insert error: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        if conn:
            try:
                conn.rollback()
                return_db_connection(conn)
            except:
                pass
        return 0


def consume_batch():
    """Read and process a batch of messages."""
    try:
        # ALWAYS check for pending messages first (they are stuck!)
        try:
            pending_info = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
            if pending_info and pending_info.get('pending', 0) > 0:
                pending_count = pending_info['pending']
                print(f"Found {pending_count} pending messages, claiming and processing...")
                
                # Get pending messages for our consumer or any consumer
                try:
                    # Try to get pending messages for this consumer first
                    pending_list = redis_client.xpending_range(
                        STREAM_KEY, CONSUMER_GROUP, '-', '+', min(pending_count, BATCH_SIZE), CONSUMER_NAME
                    )
                    
                    # If none for this consumer, get any pending messages
                    if not pending_list:
                        pending_list = redis_client.xpending_range(
                            STREAM_KEY, CONSUMER_GROUP, '-', '+', min(pending_count, BATCH_SIZE)
                        )
                    
                    if pending_list:
                        msg_ids_to_claim = []
                        for msg in pending_list:
                            if isinstance(msg, dict):
                                msg_ids_to_claim.append(msg.get('message_id'))
                            elif isinstance(msg, (list, tuple)) and len(msg) > 0:
                                msg_ids_to_claim.append(msg[0])
                        
                        if msg_ids_to_claim:
                            # Filter out None values
                            msg_ids_to_claim = [m for m in msg_ids_to_claim if m]
                            
                            if msg_ids_to_claim:
                                # Claim messages immediately (min_idle_time=0 means claim any pending message)
                                claimed = redis_client.xclaim(
                                    STREAM_KEY, CONSUMER_GROUP, CONSUMER_NAME, 0, msg_ids_to_claim
                                )
                                if claimed:
                                    print(f"Claimed {len(claimed)} pending messages")
                                    # Process claimed messages immediately
                                    claimed_records = []
                                    claimed_ids = []
                                    for claim_item in claimed:
                                        if isinstance(claim_item, (list, tuple)) and len(claim_item) >= 2:
                                            msg_id = claim_item[0]
                                            msg_data = claim_item[1]
                                        elif isinstance(claim_item, dict):
                                            # Sometimes it's a dict
                                            msg_id = claim_item.get('message_id')
                                            msg_data = {k: v for k, v in claim_item.items() if k != 'message_id'}
                                        else:
                                            continue
                                        
                                        status, metadata = process_message(msg_data, message_id=msg_id)
                                        if status == 'success':
                                            claimed_records.append(metadata)
                                            claimed_ids.append(msg_id)
                                    
                                    # Batch insert claimed messages
                                    if claimed_records:
                                        inserted = batch_insert_to_db(claimed_records)
                                        if inserted > 0:
                                            for msg_id in claimed_ids:
                                                redis_client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                                                redis_client.xdel(STREAM_KEY, msg_id)
                                            print(f"Processed {inserted} claimed pending messages")
                                            return inserted  # Return early, we processed pending messages
                except Exception as claim_error:
                    print(f"Could not claim pending messages: {claim_error}")
                    # Continue to process new messages anyway
        except redis.exceptions.ResponseError as e:
            if 'NOGROUP' not in str(e):
                print(f"Error checking pending: {e}")
        except Exception as e:
            pass  # Continue with normal processing
        
        # Process new messages (use '>' to only get new messages - never read pending ones here!)
        messages = redis_client.xreadgroup(
            CONSUMER_GROUP,
            CONSUMER_NAME,
            {STREAM_KEY: '>'},  # Only new messages, NOT pending ones
            count=BATCH_SIZE,
            block=BLOCK_MS
        )
        
        # If no new messages, return (don't try to read pending - that causes duplicates!)
        if not messages:
            return 0
        
        successful_records = []
        message_ids_to_ack = []
        message_ids_to_skip = []
        
        msg_count = sum(len(msgs) for _, msgs in messages)
        print(f"Consumer: Processing {msg_count} new messages")
        
        for stream_name, stream_messages in messages:
            for message_id, message_data in stream_messages:
                status, metadata = process_message(message_data, message_id=message_id)
                
                if status == 'success':
                    successful_records.append(metadata)
                    message_ids_to_ack.append(message_id)
                elif status == 'skip':
                    message_ids_to_skip.append(message_id)
                elif status == 'error':
                    print(f"Message {message_id} failed to process, will retry")
                    # Don't acknowledge, let it be retried
        
        # Batch insert
        processed_count = 0
        if successful_records:
            print(f"Consumer: Attempting to insert {len(successful_records)} records to database")
            inserted = batch_insert_to_db(successful_records)
            
            if inserted > 0:
                for msg_id in message_ids_to_ack:
                    redis_client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                    redis_client.xdel(STREAM_KEY, msg_id)
                processed_count = inserted
                print(f"Consumer: Acknowledged {processed_count} messages")
            else:
                print(f"Consumer: Database insert failed! Records not inserted.")
                # Don't acknowledge if insert failed - messages will be retried
        else:
            if message_ids_to_skip:
                print(f"Consumer: {len(message_ids_to_skip)} messages skipped (no valid data)")
            else:
                print("Consumer: No successful records to insert")
        
        # Skip failed messages (file not found, etc.)
        if message_ids_to_skip:
            print(f"Consumer: Skipping {len(message_ids_to_skip)} messages")
            for msg_id in message_ids_to_skip:
                redis_client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                redis_client.xdel(STREAM_KEY, msg_id)
        
        return processed_count
        
    except redis.exceptions.ResponseError as e:
        if 'NOGROUP' in str(e):
            print(f"Consumer group not found, initializing...")
            init_redis_stream()
            # Retry immediately after creating group
            return consume_batch()
        else:
            print(f"Consumer Redis error: {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
        return 0
    except Exception as e:
        print(f"Consumer error: {e}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return 0


def consumer_worker():
    """Background consumer worker thread - runs continuously."""
    global consumer_running, db_pool
    
    print(f"Consumer worker thread running")
    print(f"   Stream: {STREAM_KEY}")
    print(f"   Consumer Group: {CONSUMER_GROUP}")
    print(f"   Consumer Name: {CONSUMER_NAME}")
    print(f"   Batch Size: {BATCH_SIZE}")
    print(f"   Block Time: {BLOCK_MS}ms")
    print()
    
    total_processed = 0
    consecutive_empty = 0
    error_count = 0
    
    # Wait for database pool to be initialized
    db_wait_count = 0
    while not db_pool and consumer_running and db_wait_count < 20:
        print(f"Waiting for database pool initialization... ({db_wait_count}/20)")
        time.sleep(1)
        db_wait_count += 1
    
    if not db_pool:
        print("ERROR: Database pool not initialized after 20 seconds!")
        print("Consumer worker cannot continue without database connection.")
        return
    
    print("Database pool ready, starting message processing...")
    print()
    
    while consumer_running:
        try:
            # Always try to process messages
            count = consume_batch()
            
            if count > 0:
                total_processed += count
                consecutive_empty = 0
                error_count = 0
                print(f"Consumer: {count} processed (total: {total_processed})")
            else:
                consecutive_empty += 1
                error_count = 0
                
                # Aggressively check for messages every few cycles
                if consecutive_empty % 5 == 0:  # Every 5 cycles (~2.5 seconds)
                    try:
                        # Check queue length
                        queue_len = redis_client.xlen(STREAM_KEY)
                        
                        # Check pending messages
                        pending_count = 0
                        try:
                            pending_info = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
                            pending_count = pending_info.get('pending', 0) if pending_info else 0
                        except:
                            pass
                        
                        if queue_len > 0 or pending_count > 0:
                            print(f"Consumer: {queue_len} in queue, {pending_count} pending - processing now...")
                            # Force process (consume_batch already handles both)
                            count = consume_batch()
                            if count > 0:
                                total_processed += count
                                consecutive_empty = 0
                                print(f"Consumer: Processed {count} messages (total: {total_processed})")
                    except Exception as check_error:
                        print(f"Error checking queue: {check_error}")
            
            # Very short delay to process messages quickly
            # The block time in xreadgroup already handles waiting for new messages
            if count == 0:
                # No messages processed, block time already passed in xreadgroup
                pass  # No additional sleep needed
            else:
                # Just processed messages, tiny delay to prevent CPU spinning
                time.sleep(0.05)  # 50ms delay after processing
            
        except KeyboardInterrupt:
            print("Consumer worker interrupted")
            consumer_running = False
            break
        except Exception as e:
            error_count += 1
            consecutive_empty = 0
            print(f"Consumer worker error ({error_count}): {e}")
            import traceback
            print(f"   Traceback: {traceback.format_exc()}")
            
            # Check if database connection is still valid
            if not db_pool:
                print("Database pool is None, attempting to reinitialize...")
                try:
                    init_db_pool()
                except Exception as db_err:
                    print(f"Failed to reinitialize database pool: {db_err}")
            
            # Wait before retry, but not too long
            wait_time = min(2 * error_count, 10)  # Max 10 seconds
            time.sleep(wait_time)
            
            # If errors persist, try to reinitialize
            if error_count > 5:
                print("Multiple errors, reinitializing Redis stream and database...")
                try:
                    init_redis_stream()
                    if not db_pool:
                        init_db_pool()
                except Exception as init_err:
                    print(f"Reinitialization error: {init_err}")
                error_count = 0
    
    print("Consumer worker stopped")


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Root page."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>ConnectStorm System</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
            }
            h1 { color: #2c3e50; }
            a {
                display: inline-block;
                margin: 10px;
                padding: 15px 30px;
                background: #3498db;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
            }
            a:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <h1>ConnectStorm System</h1>
        <p>Distributed file ingestion with Redis Streams & TimescaleDB</p>
        <div>
            <a href="/upload">Upload Files</a>
            <a href="/dashboard">Dashboard</a>
        </div>
    </body>
    </html>
    '''


@app.route('/upload')
def upload_page():
    """Serve upload page."""
    return render_template('upload.html')


@app.route('/dashboard')
def dashboard_page():
    """Serve dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Handle file upload."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        filename = secure_filename(file.filename)
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')
        safe_filename = f"{timestamp}_{filename}"
        
        tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
        file.save(tmp_path)
        
        file_size = os.path.getsize(tmp_path)
        mime_type = file.content_type or 'application/octet-stream'
        uploader_id = request.form.get('uploader_id', 'anonymous')
        
        # Upload to storage
        try:
            storage_url = upload_file(tmp_path, filename)
            try:
                os.remove(tmp_path)
            except:
                pass
        except Exception as e:
            try:
                os.remove(tmp_path)
            except:
                pass
            return jsonify({'error': f'Storage upload failed: {str(e)}'}), 500
        
        # Add to Redis
        metadata = {
            'operation': 'UPLOAD',
            'filename': filename,
            'size': str(file_size),
            'mime_type': mime_type,
            'storage_url': storage_url,
            'uploader_id': uploader_id,
            'ts': datetime.now(timezone.utc).isoformat(),
            'already_stored': 'true'
        }
        
        stream_id = redis_client.xadd(STREAM_KEY, metadata)
        
        return jsonify({
            'success': True,
            'message': 'File uploaded and queued',
            'filename': filename,
            'size': file_size,
            'storage_url': storage_url,
            'stream_id': stream_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@app.route('/api/counts', methods=['GET'])
def api_counts():
    """Return counts."""
    try:
        redis_count = redis_client.xlen(STREAM_KEY)
        
        timescale_count = 0
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM file_events")
            timescale_count = cur.fetchone()[0]
            cur.close()
            return_db_connection(conn)
        except:
            pass
        
        return jsonify({
            'redis': redis_count,
            'timescale': timescale_count,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e), 'redis': 0, 'timescale': 0}), 500


@app.route('/health')
def health():
    """Health check."""
    try:
        redis_client.ping()
        conn = get_db_connection()
        return_db_connection(conn)
        
        # Check queue length
        queue_len = redis_client.xlen(STREAM_KEY)
        
        status = {
            'status': 'healthy',
            'consumer_enabled': ENABLE_CONSUMER,
            'consumer_running': consumer_running,
            'queue_length': queue_len,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


@app.route('/api/trigger-consumer', methods=['POST'])
def trigger_consumer():
    """Manually trigger consumer to process messages (for debugging)."""
    if not ENABLE_CONSUMER:
        return jsonify({'error': 'Consumer is disabled'}), 400
    
    try:
        # Process one batch manually
        count = consume_batch()
        queue_len = redis_client.xlen(STREAM_KEY)
        
        return jsonify({
            'success': True,
            'processed': count,
            'queue_remaining': queue_len,
            'message': f'Processed {count} messages, {queue_len} remaining'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# STARTUP
# ============================================================================

def process_all_pending_messages():
    """Process all pending/stuck messages immediately on startup."""
    if not ENABLE_CONSUMER or not db_pool:
        return
    
    print("Checking for pending/stuck messages on startup...")
    try:
        # Check for pending messages
        try:
            pending_info = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
            if pending_info and pending_info.get('pending', 0) > 0:
                pending_count = pending_info['pending']
                print(f"Found {pending_count} pending messages, processing now...")
                
                # Process pending messages
                processed = 0
                max_iterations = min(pending_count + 10, 50)
                for _ in range(max_iterations):
                    count = consume_batch()
                    if count == 0:
                        try:
                            pending_info = redis_client.xpending(STREAM_KEY, CONSUMER_GROUP)
                            new_pending = pending_info.get('pending', 0) if pending_info else 0
                            if new_pending == 0:
                                break
                        except:
                            break
                    processed += count
                    if processed >= pending_count:
                        break
                    time.sleep(0.2)
                
                if processed > 0:
                    print(f"Processed {processed} pending messages on startup")
        except redis.exceptions.ResponseError as e:
            if 'NOGROUP' not in str(e):
                print(f"Error checking pending: {e}")
        
        # Also process any new messages in queue
        queue_len = redis_client.xlen(STREAM_KEY)
        if queue_len > 0:
            print(f"Found {queue_len} messages in queue, processing now...")
            processed = 0
            for _ in range(min(queue_len, 50)):
                count = consume_batch()
                if count == 0:
                    break
                processed += count
                time.sleep(0.1)
            
            if processed > 0:
                print(f"Processed {processed} queued messages on startup")
    except Exception as e:
        print(f"Error processing pending messages: {e}")


def start_consumer():
    """Start consumer in background thread."""
    global consumer_thread, consumer_running
    
    if ENABLE_CONSUMER:
        consumer_running = True
        
        # Process any pending messages immediately (synchronously) BEFORE starting thread
        process_all_pending_messages()
        
        # Start the continuous consumer thread (non-daemon so it keeps running)
        consumer_thread = threading.Thread(target=consumer_worker, daemon=False, name="ConsumerWorker")
        consumer_thread.start()
        print("Consumer worker thread started")
    else:
        print("Consumer disabled (set ENABLE_CONSUMER=true to enable)")


# ============================================================================
# APP INITIALIZATION (runs on import for WSGI servers like Render)
# ============================================================================

_initialized = False

def initialize_app():
    """Initialize database, Redis, and start consumer. Safe to call multiple times."""
    global _initialized, consumer_thread, consumer_running
    
    if _initialized:
        return
    
    print("=" * 70)
    print("CONNECTSTORM (COMBINED APP + CONSUMER) - INITIALIZING")
    print("=" * 70)
    print(f"Storage mode: {STORAGE_MODE}")
    print(f"Consumer enabled: {ENABLE_CONSUMER}")
    print()
    
    if STORAGE_MODE == 'local':
        print("WARNING: local storage won't work with distributed deployment!")
        print()
    
    # Setup database and Redis FIRST
    print("Initializing database...")
    db_ok = init_db_pool()
    if not db_ok:
        print("WARNING: Database pool initialization failed!")
        print("   Consumer may not work properly")
        print()
    else:
        print("Database pool initialized successfully")
    
    print("Initializing Redis stream...")
    init_redis_stream()
    print("Redis stream initialized")
    print()
    
    # Start consumer in background
    if ENABLE_CONSUMER and db_ok:
        print("Starting consumer worker...")
        start_consumer()
        
        # Give consumer thread a moment to start
        time.sleep(1)
        
        # Verify consumer is running
        if consumer_thread and consumer_thread.is_alive():
            print("✓ Consumer thread is running")
        else:
            print("WARNING: Consumer thread may not be running!")
    elif not ENABLE_CONSUMER:
        print("Consumer is DISABLED!")
        print("   Set ENABLE_CONSUMER=true to enable consumer")
    elif not db_ok:
        print("Consumer NOT started - database initialization failed")
    
    print()
    _initialized = True

# Initialize when module is imported (works with WSGI servers)
# Use threading to avoid blocking
def _init_in_background():
    """Initialize app in background thread to avoid blocking."""
    try:
        init_thread = threading.Thread(target=initialize_app, daemon=True, name="AppInitializer")
        init_thread.start()
        # Give it a moment to start, but don't block
        time.sleep(0.5)
    except Exception as e:
        print(f"Error starting initialization thread: {e}")
        # Fallback: initialize directly
        initialize_app()

# For WSGI servers (Render, gunicorn, etc.), initialize on first request
@app.before_request
def before_request():
    """Ensure initialization and consumer are running."""
    global _initialized
    if not _initialized:
        # Initialize synchronously on first request to avoid race conditions
        initialize_app()

# Initialize immediately when module loads (works for direct execution and WSGI setups)
# This ensures consumer starts even when app is imported by gunicorn
_init_in_background()


if __name__ == '__main__':
    # Wait for initialization to complete
    print("Waiting for initialization...")
    max_wait = 10
    waited = 0
    while not _initialized and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5
    
    if not _initialized:
        print("Initialization taking longer than expected, continuing anyway...")
        initialize_app()  # Force initialization
    
    # Run Flask (this blocks the main thread, but consumer runs in background)
    port = int(os.getenv('PORT', os.getenv('FLASK_PORT', 8080)))
    print(f"Starting Flask on port {port}...")
    print("=" * 70)
    print()
    print("Consumer is processing messages in the background")
    print("   Check logs for consumer activity")
    print()
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)
    finally:
        # Cleanup on shutdown
        consumer_running = False
        if consumer_thread:
            consumer_thread.join(timeout=5)
        if db_pool:
            db_pool.closeall()

