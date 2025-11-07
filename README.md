# ⚡ ConnectStorm

A cloud-ready distributed file ingestion system using **Flask**, **Redis Streams**, **TimescaleDB**, **S3/R2**, and **Selenium**, designed for deployment on **Render Free Tier**.

---

## 🎯 Overview

ConnectStorm is a complete distributed file ingestion system that simulates real users uploading files to a web application. It demonstrates:

- **Distributed Queue Processing** with Redis Streams
- **Time-Series Data Storage** with TimescaleDB
- **Object Storage** with S3/Cloudflare R2
- **Real User Simulation** with Selenium WebDriver
- **Cloud Deployment** on Render Free Tier

---

## 🏗️ Architecture

```
┌─────────────┐
│   Browser   │──────────────┐
│  (Upload)   │              │
└─────────────┘              │
                             ▼
┌─────────────┐        ┌──────────┐        ┌─────────────┐
│  Selenium   │───────▶│  Flask   │───────▶│   Redis     │
│  Producer   │        │   Web    │        │   Stream    │
└─────────────┘        └──────────┘        └──────┬──────┘
                             │                    │
                             │                    ▼
                             │             ┌─────────────┐
                             │             │  Consumer   │
                             │             │   Worker    │
                             │             └──────┬──────┘
                             │                    │
                             ▼                    ▼
                       ┌──────────┐        ┌─────────────┐
                       │    S3    │        │ TimescaleDB │
                       │   / R2   │        │  (Postgres) │
                       └──────────┘        └─────────────┘
```

---

## 🚀 Features

### User-Facing Web Application

- ✅ **Upload Page** - Simple HTML form for file uploads
- ✅ **Dashboard** - Real-time metrics with auto-refresh
- ✅ **REST API** - `/api/upload` and `/api/counts` endpoints

### Backend Infrastructure

- ✅ **Redis Stream Queue** - Reliable message queue with consumer groups
- ✅ **Consumer Worker** - Batch processing with XACK/XDEL
- ✅ **TimescaleDB** - Time-series hypertable for file events
- ✅ **S3/R2 Storage** - Object storage with fallback to local

### Automation & Testing

- ✅ **Selenium Producer** - Headless Chrome automation
- ✅ **Concurrent Users** - Multi-threaded upload simulation
- ✅ **Real User Behavior** - Random delays and file selection

### Cloud Deployment

- ✅ **Render Blueprint** - Infrastructure as code with `render.yaml`
- ✅ **Free Tier Compatible** - Optimized for free hosting
- ✅ **External Services** - Managed Redis, TimescaleDB, and S3

---

## 📁 Project Structure

```
ConnectStorm/
├── app.py                  # Flask web application
├── consumer.py             # Redis Stream consumer worker
├── storage.py              # S3/R2/local storage handler
├── selenium_producer.py    # Selenium automation producer
├── schema.sql              # TimescaleDB schema
├── requirements.txt        # Python dependencies
├── render.yaml             # Render deployment config
├── deploy.md               # Deployment guide
├── env.example             # Environment variable template
├── templates/
│   ├── upload.html         # Upload page UI
│   └── dashboard.html      # Dashboard page UI
└── files/                  # Sample files for upload
```

---

## 🛠️ Quick Start

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

Copy `env.example` to `.env` and update with your credentials:

```bash
cp env.example .env
# Edit .env with your Redis, PostgreSQL, and S3 credentials
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

### 6. Run Services

```bash
# Terminal 1: Flask Web
python app.py

# Terminal 2: Consumer Worker
python consumer.py

# Terminal 3: Selenium Producer
python selenium_producer.py
```

### 7. Access Application

- **Upload Page**: http://localhost:8080/upload
- **Dashboard**: http://localhost:8080/dashboard

---

## 🌐 Deployment

See **[deploy.md](deploy.md)** for complete deployment instructions.

### Quick Deploy to Render

1. Push code to GitHub
2. Connect repository to Render
3. Configure environment variables
4. Deploy using `render.yaml` blueprint

---

## 🔧 Configuration

### Environment Variables

| Variable              | Description                       | Default                  |
| --------------------- | --------------------------------- | ------------------------ |
| `FLASK_PORT`          | Flask server port                 | `8080`                   |
| `SECRET_KEY`          | Flask secret key                  | `dev`                    |
| `REDIS_URL`           | Redis connection URL              | `redis://localhost:6379` |
| `PG_URI`              | PostgreSQL connection URL         | `postgres://...`         |
| `STORAGE_MODE`        | Storage backend (`s3` or `local`) | `s3`                     |
| `S3_BUCKET`           | S3/R2 bucket name                 | -                        |
| `PRODUCER_USERS`      | Concurrent Selenium users         | `5`                      |
| `PRODUCER_REPEATS`    | Uploads per user                  | `2`                      |
| `CONSUMER_BATCH_SIZE` | Redis batch size                  | `10`                     |

---

## 📊 Monitoring

### Check Redis Queue

```bash
redis-cli -u $REDIS_URL XLEN ConnectStorm:uploads
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

---

## 🧪 Testing

### Manual Upload Test

1. Visit `/upload`
2. Select a file
3. Optional: Enter uploader ID
4. Click "Upload File"
5. Check `/dashboard` for updates

### Automated Upload Test

```bash
python selenium_producer.py
```

This will:

- Spawn 5 concurrent users (configurable)
- Each uploads 2 random files from `files/`
- Simulates real user behavior with delays

---

## 📈 Performance

### Render Free Tier Limits

- **750 hours/month** per service
- **512 MB RAM** per service
- **0.1 CPU** per service

### Optimization Tips

1. Keep `PRODUCER_USERS` between 3-5
2. Use `CONSUMER_BATCH_SIZE=10-20`
3. Add delays between uploads
4. Monitor resource usage in Render dashboard

---

## 🔐 Security

- ✅ Use strong `SECRET_KEY`
- ✅ Enable SSL for Redis (`rediss://`)
- ✅ Use `sslmode=require` for PostgreSQL
- ✅ Restrict S3 bucket permissions
- ✅ Never commit `.env` file
- ✅ Use environment variables in production

---

## 🐛 Troubleshooting

### Web Service Won't Start

- Check Redis and PostgreSQL connections
- Verify schema.sql was applied
- Check logs for Python errors

### Consumer Not Processing

- Verify Redis Stream exists
- Check consumer group is created
- Test S3 credentials

### Selenium Fails

- Ensure Chrome is installed
- Use `PRODUCER_HEADLESS=true` on servers
- Verify target URL is accessible

See **[deploy.md](deploy.md)** for detailed troubleshooting.

---

## 📚 API Documentation

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
  "message": "File uploaded and queued for processing",
  "filename": "example.txt",
  "size": 1024,
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
  "timestamp": "2025-11-07T12:30:00Z"
}
```

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Add authentication/authorization
- [ ] Implement file type validation
- [ ] Add virus scanning
- [ ] Create admin dashboard
- [ ] Add WebSocket for real-time updates
- [ ] Implement rate limiting
- [ ] Add comprehensive tests

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Flask** - Web framework
- **Redis** - Stream processing
- **TimescaleDB** - Time-series database
- **Selenium** - Browser automation
- **Render** - Cloud hosting

---

## 📞 Support

For issues and questions:

- **GitHub Issues**: [Create an issue](https://github.com/yourusername/ConnectStorm/issues)
- **Documentation**: See [deploy.md](deploy.md)

---

**Built with ❤️ for distributed systems learning**
