# ⚡ Quick Start - Deploy to Render

## ✅ You're All Set!

Your `app.py` now includes both frontend + consumer in one file.

---

## 🚀 Deploy to Render (3 Steps)

### 1. Add Environment Variable to .env

Add this line to your `.env` file:

```env
ENABLE_CONSUMER=true
```

### 2. Push to GitHub

```bash
git add .
git commit -m "Updated to combined app with consumer"
git push
```

### 3. Set Environment Variables in Render

Go to your Render dashboard → Your service → Environment

Add these variables:

```
ENABLE_CONSUMER=true
STORAGE_MODE=s3
REDIS_URL=redis://default:password@host:port
PG_URI=postgresql://user:password@host:port/dbname?sslmode=require
S3_ENDPOINT=https://...
S3_BUCKET=your-bucket
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_PUBLIC_BASE_URL=https://...
```

**That's it!** Render will auto-deploy when you push.

---

## 🧪 Test Locally First

```bash
# Add to .env:
ENABLE_CONSUMER=true

# Run
python app.py

# Should see:
# ✓ Consumer worker thread started
# 🌐 Starting Flask on port 8080...

# Test upload:
# Go to http://localhost:8080/upload
```

---

## 📊 Verify It's Working

### Check Render Logs

You should see:
```
✓ Database connection pool initialized
✓ Consumer group 'connectstorm_group' already exists
✓ Consumer worker thread started
🌐 Starting Flask on port 8080...
```

### Upload a File

1. Go to: `https://your-app.onrender.com/upload`
2. Upload a test file
3. Check logs for: `✓ Consumer: 1 processed`

### Check Dashboard

Go to: `https://your-app.onrender.com/dashboard`

Should show:
- Redis: 0 (processed immediately)
- TimescaleDB: 1+ (records stored)

---

## 🔧 Configuration

### Required Environment Variables

| Variable | Example | Note |
|----------|---------|------|
| `ENABLE_CONSUMER` | `true` | **NEW!** Enables background consumer |
| `STORAGE_MODE` | `s3` | Must be `s3` for cloud |
| `REDIS_URL` | `redis://...` | Your Redis Cloud URL |
| `PG_URI` | `postgresql://...` | TimescaleDB connection |
| `S3_ENDPOINT` | `https://...` | S3/R2 endpoint |
| `S3_BUCKET` | `mybucket` | Your bucket name |
| `S3_ACCESS_KEY` | `...` | S3 access key |
| `S3_SECRET_KEY` | `...` | S3 secret key |
| `S3_PUBLIC_BASE_URL` | `https://...` | Public URL for files |

### Optional Tuning

```env
CONSUMER_BATCH_SIZE=50      # Files per batch (default: 50)
CONSUMER_BLOCK_MS=1000      # Polling interval (default: 1000ms)
```

---

## 📁 File Structure (After Cleanup)

**Main Files:**
- ✅ `app.py` - Combined frontend + consumer
- ✅ `consumer.py` - Standalone consumer (for Option 2 later)
- ✅ `storage.py` - S3/R2 handler
- ✅ `schema.sql` - Database schema

**Backup Files (safe to delete):**
- `app_local_backup.py` - Original separate frontend
- `app_old_backup.py` - Previous app.py version
- `consumer_local_backup.py` - Original separate consumer

**Tools:**
- `status.py` - Check system status
- `reset.py` - Clear data
- `healthcheck.py` - Health monitoring
- `selenium_producer.py` - Load testing

**Guides:**
- `README.md` - Main documentation
- `RENDER_DEPLOYMENT.md` - Detailed Render guide
- `DEPLOYMENT_OPTIONS.md` - All deployment options
- `QUICKSTART.md` - This file!

---

## 🆘 Troubleshooting

### Consumer not running?

**Check logs for:**
```
✓ Consumer worker thread started
```

**If missing, verify:**
```env
ENABLE_CONSUMER=true  ← Must be set!
```

### Files not uploading?

**Verify:**
```env
STORAGE_MODE=s3  ← NOT 'local'!
```

### Service sleeping?

Render free tier sleeps after 15 min.

**Solution:** Use [UptimeRobot](https://uptimerobot.com/) (free) to ping:
```
https://your-app.onrender.com/health
```
Every 5 minutes.

### Need more help?

Read the detailed guides:
- `RENDER_DEPLOYMENT.md` - Full deployment guide
- `DEPLOYMENT_OPTIONS.md` - Understand all options
- `PERFORMANCE.md` - Optimization tips

---

## 🎉 Success!

Once deployed, your app will:
1. ✅ Accept file uploads via web interface
2. ✅ Store files in S3/R2
3. ✅ Process them in background (same process)
4. ✅ Save metadata to TimescaleDB
5. ✅ Show real-time stats on dashboard

**Everything runs in one process on Render free tier!**

---

## 📊 Check Status Anytime

```bash
# Local:
python status.py

# Cloud:
curl https://your-app.onrender.com/health
curl https://your-app.onrender.com/api/counts
```

---

**That's it! You're ready to deploy! 🚀**

