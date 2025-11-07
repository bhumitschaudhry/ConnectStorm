# 📦 Deployment Options

## Which Files to Use?

### Option 1: Combined (Render Free Tier) ⭐ **RECOMMENDED FOR YOU**

**Use:** `app.py` (combined version - includes consumer)

**When:**
- ✅ Deploying to Render **FREE tier**
- ✅ Can't run separate worker processes
- ✅ Low to moderate traffic (<100 files/min)
- ✅ Want simplest deployment

**Setup:**
```bash
# Render start command:
python app.py
```

**Pros:**
- ✅ Works on free tier
- ✅ Single process
- ✅ Consumer runs automatically
- ✅ Simple deployment

**Cons:**
- ⚠️ Can't scale consumer independently
- ⚠️ Limited by single instance resources

**Guide:** `RENDER_DEPLOYMENT.md`

---

### Option 2: Separate Services (Production)

**Use:** `consumer.py` on separate machine (frontend uses app.py)

**When:**
- ✅ Production deployment
- ✅ High traffic (>100 files/min)
- ✅ Need independent scaling
- ✅ Have budget for multiple services

**Setup:**
```bash
# Machine 1 (Frontend):
python app.py

# Machine 2 (Consumer):
python consumer.py

# Machine 3 (Another Consumer - optional):
CONSUMER_NAME=consumer_2 python consumer.py
```

**Pros:**
- ✅ Can scale independently
- ✅ Multiple consumers possible
- ✅ Better fault tolerance
- ✅ Higher throughput

**Cons:**
- ⚠️ Requires multiple services
- ⚠️ More complex deployment
- ⚠️ Higher cost

**Guide:** `CLOUD_DEPLOYMENT.md`

---

### Option 3: Local Development

**Use:** `app_local_backup.py` + `consumer_local_backup.py`

**When:**
- ✅ Testing on local machine
- ✅ Both services on same computer
- ✅ Using local file storage
- ✅ Development only

**Setup:**
```bash
# Terminal 1:
python app_local_backup.py

# Terminal 2:
python consumer_local_backup.py
```

**Pros:**
- ✅ Simple local testing
- ✅ No cloud storage needed
- ✅ Fast iteration

**Cons:**
- ⚠️ Won't work in cloud
- ⚠️ No distributed deployment
- ⚠️ Local storage only

**Guide:** `local.md`

---

## Quick Decision Tree

```
Are you deploying to Render FREE tier?
│
├─ YES → Use app.py with ENABLE_CONSUMER=true (Option 1)
│        Read: RENDER_DEPLOYMENT.md
│
└─ NO → Do you need high throughput (>100 files/min)?
        │
        ├─ YES → Use app.py + separate consumer.py (Option 2)
        │        Read: CLOUD_DEPLOYMENT.md
        │
        └─ NO → Use app.py with ENABLE_CONSUMER=true (simpler)
                 Works on any cloud platform
```

---

## Environment Variables

### Required for ALL options:

```env
# Redis
REDIS_URL=redis://default:password@host:port

# TimescaleDB
PG_URI=postgresql://user:password@host:port/dbname?sslmode=require

# Storage (CRITICAL for cloud!)
STORAGE_MODE=s3  # NOT 'local' for cloud deployment

# S3/R2
S3_ENDPOINT=https://...
S3_BUCKET=your-bucket
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_PUBLIC_BASE_URL=https://...
```

### Additional for Option 1 (Combined):

```env
# Enable consumer in background
ENABLE_CONSUMER=true

# Performance tuning
CONSUMER_BATCH_SIZE=50
CONSUMER_BLOCK_MS=1000
```

---

## File Mapping

| Purpose | Option 1 (Combined) | Option 2 (Separate) | Option 3 (Local) |
|---------|-------------------|-------------------|----------------|
| **Frontend** | app.py | app.py | app_local_backup.py |
| **Consumer** | (built-in) | consumer.py | consumer_local_backup.py |
| **Runs on** | Single process | Multiple machines | Same machine |
| **Storage** | S3/R2 required | S3/R2 required | Local OK |

---

## Your Situation

Based on your requirements:

> "The frontend (app.py) is hosted on render. The consumer will be hosted somewhere else as our plan doesn't allow to run consumer on render"

**✅ SOLUTION: Use `app.py` with `ENABLE_CONSUMER=true`**

This runs both frontend AND consumer in a single process, which works on Render free tier!

**Steps:**
1. Read `RENDER_DEPLOYMENT.md`
2. Configure S3/R2 storage
3. Push to GitHub (Render auto-deploys)
4. Set `ENABLE_CONSUMER=true` in Render environment
5. Done! Both services run together

**You DON'T need to deploy consumer separately!**

---

## Testing Locally First

Before deploying to Render, test the combined app locally:

```bash
# 1. Set environment variables
cp .env.example .env
# Edit .env with your credentials
# Add: ENABLE_CONSUMER=true

# 2. Run app
python app.py

# 3. Upload a file
# Go to http://localhost:8080/upload

# 4. Check logs
# Should see:
# ✓ Consumer worker thread started
# ✓ Consumer: 1 processed (total: 1)
```

---

## Migration Path

### Currently using separate files?

**Migrate to combined:**

1. **Backup current files** (already done):
   - `app_local_backup.py`
   - `app_old_backup.py`
   - `consumer_local_backup.py`

2. **Update environment:**
   ```bash
   # Add to .env:
   ENABLE_CONSUMER=true
   ```

3. **Deploy to Render:**
   - Just push to GitHub
   - Set `ENABLE_CONSUMER=true` in Render
   - Render uses `python app.py` (already configured)

4. **Test:** Upload files and check dashboard

---

## Summary

| | Combined (FREE) | Separate (PRO) | Local (DEV) |
|---|---|---|---|
| **Cost** | $0 | $15-30/mo | $0 |
| **Complexity** | ⭐ Simple | ⭐⭐⭐ Complex | ⭐ Simple |
| **Scalability** | ~20/sec | 100+/sec | N/A |
| **Best for** | Demos, low traffic | Production | Development |
| **Your case** | ✅ **YES** | Maybe later | Testing |

**Start with Combined, upgrade to Separate if needed!**

