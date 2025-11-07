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
print(f"✓ Upload folder: {app.config['UPLOAD_FOLDER']}")

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
BLOCK_MS = int(os.getenv('CONSUMER_BLOCK_MS', '1000'))
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


def init_redis_stream():
    """Initialize Redis Stream and consumer group if not exists."""
    try:
        redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
        print(f"✓ Created consumer group '{CONSUMER_GROUP}'")
    except redis.exceptions.ResponseError as e:
        if 'BUSYGROUP' in str(e):
            print(f"✓ Consumer group '{CONSUMER_GROUP}' already exists")
        else:
            print(f"⚠ Redis error: {e}")


# ============================================================================
# CONSUMER FUNCTIONS (Background Worker)
# ============================================================================

def process_message(message_data):
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
                'uploader_id': uploader_id
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
                'uploader_id': uploader_id
            }
            return 'success', metadata
        
    except Exception as e:
        print(f"✗ Error processing message: {e}")
        return 'error', None


def batch_insert_to_db(records):
    """Insert multiple records to database."""
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
            (r['event_time'], r['operation'], r['filename'], 
             r['file_size'], r['mime_type'], r['storage_url'], r['uploader_id'])
            for r in records
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
    """Read and process a batch of messages."""
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
        
        # Batch insert
        processed_count = 0
        if successful_records:
            inserted = batch_insert_to_db(successful_records)
            
            if inserted > 0:
                for msg_id in message_ids_to_ack:
                    redis_client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
                    redis_client.xdel(STREAM_KEY, msg_id)
                processed_count = inserted
        
        # Skip failed messages
        for msg_id in message_ids_to_skip:
            redis_client.xack(STREAM_KEY, CONSUMER_GROUP, msg_id)
            redis_client.xdel(STREAM_KEY, msg_id)
        
        return processed_count
        
    except Exception as e:
        print(f"✗ Consumer error: {e}")
        return 0


def consumer_worker():
    """Background consumer worker thread."""
    global consumer_running
    
    print(f"🚀 Consumer worker started in background")
    print(f"   Stream: {STREAM_KEY}")
    print(f"   Batch Size: {BATCH_SIZE}")
    
    total_processed = 0
    idle_cycles = 0
    
    while consumer_running:
        try:
            count = consume_batch()
            total_processed += count
            
            if count > 0:
                print(f"✓ Consumer: {count} processed (total: {total_processed})")
                idle_cycles = 0
            else:
                idle_cycles += 1
                if idle_cycles % 300 == 0:  # Every 5 minutes
                    print(f"💓 Consumer idle: {idle_cycles * BLOCK_MS // 1000}s")
            
        except Exception as e:
            print(f"✗ Consumer error: {e}")
            time.sleep(5)
    
    print("⚠ Consumer worker stopped")


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
        <h1>⚡ ConnectStorm System</h1>
        <p>Distributed file ingestion with Redis Streams & TimescaleDB</p>
        <div>
            <a href="/upload">📤 Upload Files</a>
            <a href="/dashboard">📊 Dashboard</a>
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
        
        status = {
            'status': 'healthy',
            'consumer_enabled': ENABLE_CONSUMER,
            'consumer_running': consumer_running,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        return jsonify(status), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


# ============================================================================
# STARTUP
# ============================================================================

def start_consumer():
    """Start consumer in background thread."""
    global consumer_thread, consumer_running
    
    if ENABLE_CONSUMER:
        consumer_running = True
        consumer_thread = threading.Thread(target=consumer_worker, daemon=True)
        consumer_thread.start()
        print("✓ Consumer worker thread started")
    else:
        print("⚠ Consumer disabled (set ENABLE_CONSUMER=true to enable)")


if __name__ == '__main__':
    # Initialize
    print("=" * 70)
    print("CONNECTSTORM (COMBINED APP + CONSUMER)")
    print("=" * 70)
    print(f"Storage mode: {STORAGE_MODE}")
    
    if STORAGE_MODE == 'local':
        print("⚠ WARNING: local storage won't work with distributed deployment!")
    
    # Setup database and Redis
    init_db_pool()
    init_redis_stream()
    
    # Start consumer in background
    start_consumer()
    
    # Run Flask
    port = int(os.getenv('FLASK_PORT', 8080))
    print(f"\n🌐 Starting Flask on port {port}...")
    print("=" * 70)
    
    app.run(host='0.0.0.0', port=port, debug=False)  # debug=False for production

