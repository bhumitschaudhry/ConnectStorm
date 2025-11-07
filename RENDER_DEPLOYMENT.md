# 🚀 Render Deployment Guide (Free Tier)

## The Problem

Render's free tier doesn't support separate worker processes. You can't run:
- `app.py` (web server) 
- `consumer.py` (worker) ← **Not allowed on free tier!**

## The Solution

Use **`app.py`** which runs BOTH in a single process:
- Flask web server (main thread)
- Consumer worker (background thread)

```
┌─────────────────────────────────┐
│      Render (Single Process)    │
│                                  │
│  ┌────────────┐  ┌────────────┐ │
│  │   Flask    │  │  Consumer  │ │
│  │ (main      │  │  (background│ │
│  │  thread)   │  │   thread)  │ │
│  └────────────┘  └────────────┘ │
│                                  │
└─────────────────────────────────┘
          │              │
          ▼              ▼
    ┌─────────┐    ┌─────────┐
    │  Redis  │    │TimescaleDB│
    └─────────┘    └─────────┘
```

---

## Setup Steps

### 1. Configure Storage (CRITICAL!)

In your `.env` and Render environment variables:

```env
# REQUIRED: Use S3/R2 (NOT local!)
STORAGE_MODE=s3

# Cloudflare R2 (recommended - free 10GB)
S3_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
S3_REGION=auto
S3_BUCKET=your-bucket-name
S3_ACCESS_KEY=your-access-key-id
S3_SECRET_KEY=your-secret-key
S3_PUBLIC_BASE_URL=https://your-public-url.com

# Redis Cloud
REDIS_URL=redis://default:password@host:port

# TimescaleDB
PG_URI=postgresql://user:password@host:port/dbname?sslmode=require

# Enable consumer
ENABLE_CONSUMER=true

# Optional performance tuning
CONSUMER_BATCH_SIZE=50
CONSUMER_BLOCK_MS=1000
```

### 2. Deploy to Render

#### Option A: Via Dashboard

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name:** `connectstorm` (or your choice)
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
   - **Instance Type:** `Free`

5. Add Environment Variables (from `.env` above)
6. Click **"Create Web Service"**

#### Option B: Via render.yaml

Update `render.yaml`:

```yaml
services:
  - type: web
    name: connectstorm
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py
    envVars:
      - key: STORAGE_MODE
        value: s3
      - key: ENABLE_CONSUMER
        value: true
      - key: REDIS_URL
        sync: false  # Add in dashboard (secret)
      - key: PG_URI
        sync: false  # Add in dashboard (secret)
      - key: S3_ENDPOINT
        sync: false
      - key: S3_ACCESS_KEY
        sync: false
      - key: S3_SECRET_KEY
        sync: false
      - key: S3_BUCKET
        value: your-bucket-name
      - key: S3_PUBLIC_BASE_URL
        value: https://your-public-url.com
```

Then: `git push` → Render auto-deploys

---

## Testing

### 1. Check Deployment Logs

In Render dashboard → Your service → **"Logs"**

You should see:
```
✓ Database connection pool initialized
✓ Consumer group 'connectstorm_group' already exists
✓ Consumer worker thread started
🌐 Starting Flask on port 8080...
```

### 2. Test Upload

1. Go to: `https://your-app.onrender.com/upload`
2. Upload a file
3. Check logs - should show:
   ```
   ✓ Uploaded to storage: https://...
   ✓ Consumer: 1 processed (total: 1)
   ```

### 3. Check Dashboard

Go to: `https://your-app.onrender.com/dashboard`

Should show:
- Redis: 0 (processed immediately)
- TimescaleDB: 1+ (records stored)

---

## Advantages

✅ **Works on free tier** - Single process  
✅ **No external consumer needed** - Everything in one app  
✅ **Optimized** - Connection pooling, batch inserts  
✅ **Auto-scaling** - Consumer scales with web server  
✅ **Simple deployment** - One command

---

## Disadvantages

⚠️ **Limited scaling** - Can't scale consumer independently  
⚠️ **Single point of failure** - If web crashes, consumer stops too  
⚠️ **Shared resources** - Web requests compete with consumer for CPU/memory

**For production with high load:** Use separate consumer on different cloud (see CLOUD_DEPLOYMENT.md)

---

## Performance

### Free Tier Limits (Render)

- **Memory:** 512MB
- **CPU:** 0.1 CPU (shared)
- **Sleeps after 15 min inactivity**
- **750 hours/month free**

### Expected Throughput

With free tier:
- **10-20 files/second** (moderate load)
- **Batch processing:** 50 files at once
- **Good for:** Testing, demos, low-traffic apps

### Optimization Tips

1. **Reduce batch size** if hitting memory limits:
   ```env
   CONSUMER_BATCH_SIZE=20
   ```

2. **Increase block time** to reduce CPU usage:
   ```env
   CONSUMER_BLOCK_MS=2000
   ```

3. **Keep service awake** (prevent sleep):
   - Use [UptimeRobot](https://uptimerobot.com/) to ping `/health` every 5 minutes

---

## Troubleshooting

### Consumer not processing

**Check logs:**
```
✓ Consumer worker thread started  ← Should see this
```

**If not, check:**
```env
ENABLE_CONSUMER=true  ← Must be set
```

### Out of memory errors

**Reduce batch size:**
```env
CONSUMER_BATCH_SIZE=10
```

### Files not uploading to S3

**Check:**
1. `STORAGE_MODE=s3` is set
2. S3 credentials are correct
3. Bucket exists and is public (for reads)

**Test S3 connection:**
Add to logs by temporarily adding to `app.py`:
```python
print(f"S3 Endpoint: {os.getenv('S3_ENDPOINT')}")
print(f"S3 Bucket: {os.getenv('S3_BUCKET')}")
```

### Service keeps sleeping

Render free tier sleeps after 15 min of inactivity.

**Solution:**
1. Use [UptimeRobot](https://uptimerobot.com/) (free)
2. Ping `https://your-app.onrender.com/health` every 5 minutes

### Database connection errors

**Check PG_URI format:**
```
postgresql://user:password@host:port/dbname?sslmode=require
                                              ^^^^^^^^^^^^^^ Required!
```

---

## Monitoring

### Health Check

```bash
curl https://your-app.onrender.com/health
```

Response:
```json
{
  "status": "healthy",
  "consumer_enabled": true,
  "consumer_running": true,
  "timestamp": "2025-11-07T17:30:00"
}
```

### Check Counts

```bash
curl https://your-app.onrender.com/api/counts
```

Response:
```json
{
  "redis": 0,
  "timescale": 42,
  "timestamp": "2025-11-07T17:30:00"
}
```

---

## Upgrading from Free Tier

If you outgrow free tier:

### Option 1: Upgrade Render Plan ($7/month)
- More CPU/memory
- No sleep
- Better performance

### Option 2: Separate Consumer
- Keep frontend on Render
- Move consumer to AWS/GCP ($5-10/month)
- See `CLOUD_DEPLOYMENT.md`

---

## Quick Start Summary

```bash
# 1. Ensure S3/R2 is configured
# 2. Push to GitHub
git add .
git commit -m "Deploy to Render"
git push

# 3. In Render dashboard:
#    - New Web Service
#    - Connect repo
#    - Start command: python app_combined.py
#    - Add environment variables
#    - Deploy!

# 4. Test
curl https://your-app.onrender.com/health
```

That's it! Your ConnectStorm app is now running on Render free tier with built-in consumer! 🎉

