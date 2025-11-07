# ConnectStorm

A cloud-ready distributed file ingestion system using **Flask**, **Redis Streams**, **TimescaleDB**, **S3/R2**, and **Selenium**, designed for deployment on **Render Free Tier**.

---

## Overview

ConnectStorm is a complete distributed file ingestion system that simulates real users uploading files to a web application. It demonstrates:

- **Distributed Queue Processing** with Redis Streams
- **Time-Series Data Storage** with TimescaleDB
- **Object Storage** with S3/Cloudflare R2
- **Real User Simulation** with Selenium WebDriver
- **Cloud Deployment** on Render Free Tier

---

## Architecture

```
┌─────────────┐
│   Browser   │──────────────┐
│  (Upload)   │              │
└─────────────┘              │
                             ▼
┌─────────────┐        ┌──────────────┐        ┌─────────────┐
│  Selenium   │───────▶│     Flask    │───────▶│   Redis     │
│  Producer   │        │  Web Server  │        │   Stream    │
└─────────────┘        │  + Consumer  │        └──────┬──────┘
                       │  (Combined)  │               │
                       └──────┬───────┘               │
                              │                       │
                              │              Consumer Worker
                              │              (in same process)
                              │                       │
                              ▼                       ▼
                       ┌──────────┐        ┌─────────────┐
                       │    S3    │        │ TimescaleDB │
                       │   / R2   │        │  (Postgres) │
                       └──────────┘        └─────────────┘
```

The application combines the Flask web server and consumer worker in a single process (`app.py`) to run efficiently on Render's free tier. For high-traffic scenarios, `consumer.py` can be run as a separate service.

---

## Features

### User-Facing Web Application

- **Upload Page** - Simple HTML form with drag-and-drop for file uploads
- **Dashboard** - Real-time metrics with auto-refresh showing system statistics
- **REST API** - `/api/upload` and `/api/counts` endpoints for programmatic access

### Backend Infrastructure

- **Redis Stream Queue** - Reliable message queue with consumer groups for distributed processing
- **Consumer Worker** - Batch processing with automatic duplicate detection and XACK/XDEL handling
- **TimescaleDB** - Time-series hypertable for file events with continuous aggregates
- **S3/R2 Storage** - Object storage with automatic fallback to local storage

### Automation & Testing

- **Selenium Producer** - Headless Chrome automation for load testing
- **Concurrent Users** - Multi-threaded upload simulation with configurable concurrency
- **Real User Behavior** - Random delays and file selection to simulate realistic usage

### Cloud Deployment

- **Render Blueprint** - Infrastructure as code with `render.yaml`
- **Free Tier Compatible** - Optimized for free hosting with combined web+consumer process
- **External Services** - Managed Redis, TimescaleDB, and S3/R2 storage

---

## Project Structure

```
ConnectStorm/
├── app.py                  # Flask web application + consumer (combined)
├── consumer.py             # Standalone consumer worker (optional)
├── storage.py              # S3/R2/local storage handler
├── status.py               # System status checker utility
├── reset.py                # Data clearing utility
├── selenium_producer.py    # Selenium automation producer
├── schema.sql              # TimescaleDB schema
├── requirements.txt        # Python dependencies
├── runtime.txt             # Python version specification
├── render.yaml             # Render deployment config
├── documentation.md        # File documentation
├── templates/
│   ├── upload.html         # Upload page UI
│   └── dashboard.html      # Dashboard page UI
└── files/                  # Sample files for upload
```

---

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ConnectStorm.git
cd ConnectStorm
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file with your credentials:

```env
FLASK_PORT=8080
SECRET_KEY=your-secret-key-here
REDIS_URL=redis://localhost:6379
PG_URI=postgresql://user:password@localhost:5432/filestorm
STORAGE_MODE=s3
S3_ENDPOINT=https://your-endpoint.com
S3_REGION=us-east-1
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_PUBLIC_BASE_URL=https://your-public-url.com
ENABLE_CONSUMER=true
CONSUMER_BATCH_SIZE=50
CONSUMER_BLOCK_MS=500
```

### 4. Initialize Database

```bash
psql $PG_URI -f schema.sql
```

### 5. Add Test Files

```bash
mkdir -p files
echo "Test file" > files/test.txt
```

### 6. Run Application

The main `app.py` runs both the web server and consumer in a single process:

```bash
python app.py
```

Alternatively, for distributed deployment, run services separately:

```bash
# Terminal 1: Flask Web Server (consumer disabled)
ENABLE_CONSUMER=false python app.py

# Terminal 2: Consumer Worker
python consumer.py

# Terminal 3: Selenium Producer (optional)
python selenium_producer.py
```

### 7. Access Application

- **Upload Page**: http://localhost:8080/upload
- **Dashboard**: http://localhost:8080/dashboard
- **Health Check**: http://localhost:8080/health

---

## Deployment

### Deploy to Render

1. Push code to GitHub
2. Connect repository to Render
3. Configure environment variables in Render dashboard
4. Deploy using `render.yaml` blueprint or manually configure:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
   - Health Check Path: `/health`

The application is optimized for Render's free tier by combining the web server and consumer in a single process. Set `ENABLE_CONSUMER=true` to enable background processing.

---

## Configuration

### Environment Variables

| Variable                   | Description                       | Default                        |
| -------------------------- | --------------------------------- | ------------------------------ |
| `FLASK_PORT`               | Flask server port                 | `8080`                         |
| `PORT`                     | Server port (Render uses this)    | `8080`                         |
| `SECRET_KEY`               | Flask secret key                  | `dev-secret-key-change-me`     |
| `REDIS_URL`                | Redis connection URL              | `redis://localhost:6379`       |
| `PG_URI`                   | PostgreSQL connection URL         | `postgres://...`               |
| `STORAGE_MODE`             | Storage backend (`s3` or `local`) | `local`                        |
| `S3_ENDPOINT`              | S3/R2 endpoint URL                | -                              |
| `S3_REGION`                | S3 region                         | `us-east-1`                    |
| `S3_BUCKET`                | S3/R2 bucket name                 | -                              |
| `S3_ACCESS_KEY`            | S3 access key                     | -                              |
| `S3_SECRET_KEY`            | S3 secret key                     | -                              |
| `S3_PUBLIC_BASE_URL`       | Public URL base for S3 files      | -                              |
| `ENABLE_CONSUMER`          | Enable consumer worker            | `true`                         |
| `CONSUMER_BATCH_SIZE`      | Redis batch size                  | `50`                           |
| `CONSUMER_BLOCK_MS`        | Redis block timeout (ms)          | `500`                          |
| `CONSUMER_NAME`            | Consumer name for Redis group     | `consumer_{pid}`               |
| `PRODUCER_USERS`           | Concurrent Selenium users         | `5`                            |
| `PRODUCER_REPEATS`         | Uploads per user                  | `3`                            |
| `PRODUCER_HEADLESS`        | Run Selenium in headless mode     | `true`                         |
| `PRODUCER_TARGET_BASE_URL` | Target URL for producer           | `http://localhost:8080/upload` |

---

## Monitoring

### Check System Status

Use the status utility to view system health:

```bash
python status.py
```

This displays:

- Redis connection status and queue length
- TimescaleDB connection status and record counts
- Recent activity statistics
- System health summary

### Check Redis Queue

```bash
redis-cli -u $REDIS_URL XLEN connectstorm:uploads
```

### Check Database Records

```sql
SELECT COUNT(*) FROM file_events;
SELECT * FROM file_events ORDER BY event_time DESC LIMIT 10;
```

### View Dashboard

Visit `/dashboard` to see:

- Redis queue size
- TimescaleDB record count
- Processing rate (records/sec)
- Uptime timer
- Recent activity breakdown

### Health Check Endpoint

```bash
curl http://localhost:8080/health
```

Returns JSON with system status, consumer state, and queue length.

---

## Testing

### Manual Upload Test

1. Visit `/upload`
2. Select a file or drag-and-drop
3. Optional: Enter uploader ID
4. Click "Upload File"
5. Check `/dashboard` for updates

### Automated Upload Test

```bash
python selenium_producer.py
```

This will:

- Spawn 5 concurrent users (configurable via `PRODUCER_USERS`)
- Each uploads 3 random files from `files/` directory (configurable via `PRODUCER_REPEATS`)
- Simulates real user behavior with random delays

### Reset System Data

To clear all data for testing:

```bash
python reset.py
```

This requires typing 'RESET' to confirm and will:

- Clear all messages from Redis stream
- Delete all records from TimescaleDB
- Show before/after counts for verification

---

## Performance

### Render Free Tier Limits

- **750 hours/month** per service
- **512 MB RAM** per service
- **0.1 CPU** per service

### Optimization Tips

1. Keep `PRODUCER_USERS` between 3-5 for free tier
2. Use `CONSUMER_BATCH_SIZE=50` for efficient batch processing
3. Set `CONSUMER_BLOCK_MS=500` for responsive processing
4. Monitor resource usage in Render dashboard
5. Use S3/R2 storage mode for cloud deployments (local storage won't work in distributed setups)

---

## Security

- Use strong `SECRET_KEY` in production
- Enable SSL for Redis (`rediss://`) when available
- Use `sslmode=require` for PostgreSQL connections
- Restrict S3 bucket permissions appropriately
- Never commit `.env` file to version control
- Use environment variables in production (Render dashboard)
- Validate file uploads and implement file type restrictions if needed

---

## Troubleshooting

### Web Service Won't Start

- Check Redis and PostgreSQL connections
- Verify `schema.sql` was applied to database
- Check logs for Python errors
- Ensure all required environment variables are set
- Verify `ENABLE_CONSUMER` is set correctly

### Consumer Not Processing

- Verify Redis Stream exists and consumer group is created
- Check `ENABLE_CONSUMER=true` is set
- Test S3/R2 credentials if using cloud storage
- Check database connection pool is initialized
- Review consumer logs for error messages

### Selenium Fails

- Ensure Chrome/Chromium is installed
- Use `PRODUCER_HEADLESS=true` on servers
- Verify target URL is accessible
- Check that files exist in `files/` directory
- Review Selenium driver logs

### High Memory Usage

- Reduce `CONSUMER_BATCH_SIZE` if processing large files
- Lower `PRODUCER_USERS` count
- Check for memory leaks in long-running processes
- Monitor Redis queue length to prevent backlog

---

## API Documentation

### `POST /api/upload`

Upload a file to the system.

**Request:**

```
Content-Type: multipart/form-data

file: [binary file data]
uploader_id: "user_1" (optional)
```

**Response:**

```json
{
  "success": true,
  "message": "File uploaded and queued",
  "filename": "example.txt",
  "size": 1024,
  "storage_url": "https://...",
  "stream_id": "1234567890-0"
}
```

### `GET /api/counts`

Get current system metrics.

**Response:**

```json
{
  "redis": 42,
  "timescale": 1337,
  "timestamp": "2025-01-07T12:30:00Z"
}
```

### `GET /health`

Health check endpoint for monitoring and load balancers.

**Response:**

```json
{
  "status": "healthy",
  "consumer_enabled": true,
  "consumer_running": true,
  "queue_length": 5,
  "timestamp": "2025-01-07T12:30:00Z"
}
```

### `POST /api/trigger-consumer`

Manually trigger consumer to process messages (for debugging).

**Response:**

```json
{
  "message": "Consumer triggered",
  "processed": 10
}
```

---

## Contributing

Contributions welcome! Areas for improvement:

- Add authentication/authorization
- Implement file type validation and virus scanning
- Create admin dashboard with user management
- Add WebSocket support for real-time updates
- Implement rate limiting and request throttling
- Add comprehensive unit and integration tests
- Improve error handling and retry logic
- Add metrics and observability (Prometheus, etc.)

---

## License

MIT License - See LICENSE file for details

---

## Acknowledgments

- **Flask** - Web framework
- **Redis** - Stream processing and message queue
- **TimescaleDB** - Time-series database extension for PostgreSQL
- **Selenium** - Browser automation for load testing
- **Render** - Cloud hosting platform
- **Boto3** - AWS SDK for S3-compatible storage

---

## Support

For issues and questions:

- **GitHub Issues**: [Create an issue](https://github.com/yourusername/ConnectStorm/issues)
- **Documentation**: See `documentation.md` for file descriptions

---

**Built for distributed systems learning and cloud deployment**
