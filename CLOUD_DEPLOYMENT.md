# ☁️ Cloud Deployment Guide

## Architecture

```
┌──────────────┐         ┌─────────────┐         ┌──────────────┐
│   Frontend   │────────▶│ Redis Cloud │────────▶│   Consumer   │
│   (Render)   │         │             │         │  (Any Cloud) │
│   app.py     │         │             │         │ consumer.py  │
└──────────────┘         └─────────────┘         └──────────────┘
       │                                                  │
       │                                                  │
       ▼                                                  ▼
┌──────────────────────────────────────────────────────────────┐
│                        S3 / Cloudflare R2                     │
│                     (Shared File Storage)                     │
└──────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                         ┌────────────────┐
                         │  TimescaleDB   │
                         │    (Cloud)     │
                         └────────────────┘
```

---

## Key Changes for Cloud

### ✅ Fixed Issues

**Problem:** Original code saved files locally then sent file path to Redis. Consumer on different machine couldn't access those files!

**Solution:** Files are now uploaded to S3/R2 **BEFORE** adding to Redis queue. Both frontend and consumer can access them.

### Updated Files

1. **`app.py`** - Uploads files to S3/R2 first, then adds to Redis
2. **`consumer.py`** - Reads from Redis, files already in S3/R2, just inserts metadata to DB
3. **Optimizations** - Connection pooling, batch inserts (5-10x faster)

---

## Setup

### 1. Environment Variables

Create `.env` file with:

```env
# Redis Cloud
REDIS_URL=redis://default:password@your-redis-host:port

# TimescaleDB
PG_URI=postgresql://user:password@host:port/dbname?sslmode=require

# Storage (REQUIRED for cloud deployment)
STORAGE_MODE=s3

# S3/R2 Configuration
S3_ENDPOINT=https://your-account.r2.cloudflarestorage.com
S3_REGION=auto
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_PUBLIC_BASE_URL=https://your-bucket.your-domain.com

# Optional
CONSUMER_BATCH_SIZE=50
CONSUMER_BLOCK_MS=1000
```

### 2. Deploy Frontend (Render)

**On Render:**

1. Connect your GitHub repo
2. Set build command: `pip install -r requirements.txt`
3. Set start command: `python app.py`
4. Add environment variables from `.env`
5. **IMPORTANT:** Set `STORAGE_MODE=s3` (NOT `local`)

### 3. Deploy Consumer (Any Cloud)

The consumer can run anywhere (AWS EC2, Google Cloud, DigitalOcean, etc.)

**Example: AWS EC2**

```bash
# SSH into your instance
ssh your-ec2-instance

# Clone repo
git clone your-repo-url
cd ConnectStorm

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create .env with credentials
nano .env
# (paste environment variables)

# Run consumer
python consumer.py
```

**Example: Using systemd (runs on boot)**

```bash
sudo nano /etc/systemd/system/connectstorm-consumer.service
```

```ini
[Unit]
Description=ConnectStorm Consumer
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/ConnectStorm
Environment="PATH=/home/ubuntu/ConnectStorm/venv/bin"
ExecStart=/home/ubuntu/ConnectStorm/venv/bin/python consumer.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable connectstorm-consumer
sudo systemctl start connectstorm-consumer
sudo systemctl status connectstorm-consumer
```

---

## Testing

### 1. Local Testing

```bash
# Terminal 1: Flask
python app.py

# Terminal 2: Consumer  
python consumer.py

# Upload via web: http://localhost:8080/upload
```

### 2. Cloud Testing

After deployment:

1. Go to your Render URL
2. Upload a file
3. Check consumer logs - should show successful processing
4. Check dashboard - TimescaleDB count should increase

---

## Monitoring

### Check System Status

```bash
python status.py
```

Shows:
- Redis queue length
- TimescaleDB record count
- Recent activity

### Check Consumer Logs

**Render:** Check deployment logs
**EC2/Cloud:** 
```bash
sudo journalctl -u connectstorm-consumer -f
```

---

## Troubleshooting

### Files not being processed

**Check:**
1. `STORAGE_MODE=s3` is set on Render
2. S3/R2 credentials are correct
3. Consumer has same credentials in `.env`
4. Consumer is running (check logs)

### "Access Denied" S3 errors

**Fix:**
1. Verify S3_ACCESS_KEY and S3_SECRET_KEY
2. Check bucket permissions
3. Verify S3_ENDPOINT is correct

### Consumer not processing

**Fix:**
```bash
# Check Redis connection
python status.py

# Reset and restart
python reset.py  # Type RESET
python consumer.py
```

---

## Performance

Expected throughput with optimized consumer:

- **20-50 files/second** (with cloud databases)
- **Batch processing** (50 files at once)
- **Connection pooling** (reuses DB connections)
- **Minimal latency**

---

## Costs

Typical free tier usage:

- **Redis Cloud:** Free 30MB (sufficient for queue)
- **TimescaleDB:** Free tier 500MB (sufficient for testing)
- **Cloudflare R2:** Free 10GB storage
- **Render:** Free tier for frontend
- **Consumer:** $5-10/month (cheapest VPS)

---

## Security

1. **Never commit `.env`** - Already in `.gitignore`
2. **Use SSL/TLS** - `sslmode=require` in PG_URI
3. **Restrict S3 access** - Use bucket policies
4. **Rotate keys** - Change passwords periodically

---

## Next Steps

1. ✅ Set up cloud databases (Redis, TimescaleDB)
2. ✅ Set up S3/R2 storage
3. ✅ Deploy frontend to Render
4. ✅ Deploy consumer to any cloud
5. ✅ Test end-to-end
6. ✅ Monitor performance
7. ✅ Scale if needed (add more consumers)

