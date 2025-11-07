#!/usr/bin/env python3
"""
File-Storm Flask Application
Provides upload interface, dashboard, and API endpoints.
"""

import os
import json
import time
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_from_directory
from werkzeug.utils import secure_filename
import redis
import psycopg2
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp/filestorm_uploads'

# Create upload folder if it doesn't exist
Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)

# Redis connection
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Redis Stream configuration
STREAM_KEY = 'filestorm:uploads'
CONSUMER_GROUP = 'filestorm_group'

# PostgreSQL/TimescaleDB connection
PG_URI = os.getenv('PG_URI', 'postgresql://postgres:postgres@localhost:5432/filestorm')

# Allowed file extensions (optional - can be expanded)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'zip', 'csv', 'json', 'xml', 'doc', 'docx'}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(PG_URI)


def init_redis_stream():
    """Initialize Redis Stream and consumer group if not exists."""
    try:
        redis_client.xgroup_create(STREAM_KEY, CONSUMER_GROUP, id='0', mkstream=True)
        print(f"✓ Created consumer group '{CONSUMER_GROUP}' for stream '{STREAM_KEY}'")
    except redis.exceptions.ResponseError as e:
        if 'BUSYGROUP' in str(e):
            print(f"✓ Consumer group '{CONSUMER_GROUP}' already exists")
        else:
            print(f"⚠ Redis error: {e}")


@app.route('/')
def index():
    """Root redirect to upload page."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>File-Storm System</title>
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
        <h1>⚡ File-Storm System</h1>
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
    """Serve the upload page."""
    return render_template('upload.html')


@app.route('/dashboard')
def dashboard_page():
    """Serve the dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Handle file upload.
    Saves file temporarily and pushes metadata to Redis Stream.
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        try:
            # Secure the filename
            filename = secure_filename(file.filename)
            
            # Create timestamped filename to avoid collisions
            timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H-%M-%S')
            safe_filename = f"{timestamp}_{filename}"
            
            # Save file temporarily
            tmp_path = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)
            file.save(tmp_path)
            
            # Get file info
            file_size = os.path.getsize(tmp_path)
            mime_type = file.content_type or 'application/octet-stream'
            uploader_id = request.form.get('uploader_id', 'anonymous')
            
            # Prepare metadata for Redis Stream
            metadata = {
                'operation': 'UPLOAD',
                'filename': filename,
                'size': str(file_size),
                'mime_type': mime_type,
                'tmp_path': tmp_path,
                'uploader_id': uploader_id,
                'ts': datetime.utcnow().isoformat() + 'Z'
            }
            
            # Push to Redis Stream
            stream_id = redis_client.xadd(STREAM_KEY, metadata)
            
            return jsonify({
                'success': True,
                'message': 'File uploaded and queued for processing',
                'filename': filename,
                'size': file_size,
                'stream_id': stream_id
            }), 200
            
        except Exception as e:
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
    
    return jsonify({'error': 'Invalid file'}), 400


@app.route('/api/counts', methods=['GET'])
def api_counts():
    """
    Return current Redis Stream length and TimescaleDB row count.
    """
    try:
        # Get Redis Stream length
        redis_count = redis_client.xlen(STREAM_KEY)
        
        # Get TimescaleDB row count
        timescale_count = 0
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM file_events")
            timescale_count = cur.fetchone()[0]
            cur.close()
            conn.close()
        except Exception as db_error:
            print(f"Database error: {db_error}")
            # Don't fail the entire request if DB is unavailable
        
        return jsonify({
            'redis': redis_count,
            'timescale': timescale_count,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'redis': 0,
            'timescale': 0
        }), 500


@app.route('/health')
def health():
    """Health check endpoint for Render."""
    try:
        # Test Redis connection
        redis_client.ping()
        
        # Test DB connection
        conn = get_db_connection()
        conn.close()
        
        return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503


if __name__ == '__main__':
    # Initialize Redis Stream on startup
    init_redis_stream()
    
    # Run Flask app
    port = int(os.getenv('FLASK_PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=os.getenv('FLASK_ENV') == 'development')

