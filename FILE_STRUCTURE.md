# 📁 File Structure (Cloud Deployment)

## Core Application Files

```
ConnectStorm/
│
├── 🚀 MAIN APPLICATION
│   ├── app.py                      # Flask web server + consumer (combined)
│   ├── consumer.py                 # Standalone consumer (optional)
│   ├── storage.py                  # S3/R2 file storage handler
│   ├── schema.sql                  # TimescaleDB database schema
│   │
│   └── templates/                  # Flask HTML templates
│       ├── dashboard.html          # Real-time dashboard
│       └── upload.html             # File upload page
│
├── 🛠️ UTILITIES
│   ├── status.py                   # Check system status
│   ├── reset.py                    # Clear Redis & TimescaleDB
│   ├── healthcheck.py              # Health monitoring
│   └── selenium_producer.py        # Load testing (local only)
│
├── ⚙️ CONFIGURATION
│   ├── requirements.txt            # Python dependencies
│   ├── runtime.txt                 # Python version for Render
│   ├── render.yaml                 # Render deployment config
│   └── .env                        # Environment variables (not in git)
│
├── 📚 DOCUMENTATION
│   ├── README.md                   # Main documentation
│   ├── QUICKSTART.md               # ⭐ Start here!
│   ├── RENDER_DEPLOYMENT.md        # Render deployment guide
│   ├── CLOUD_DEPLOYMENT.md         # General cloud deployment
│   ├── DEPLOYMENT_OPTIONS.md       # All deployment options
│   └── PERFORMANCE.md              # Performance optimization
│
└── 🧪 TEST DATA (optional)
    └── files/                      # Sample files for testing
        ├── data.json
        ├── README.txt
        ├── sample1.txt
        └── sample2.txt
```

---

## File Purposes

### 🚀 Main Application

| File | Purpose | Required |
|------|---------|----------|
| `app.py` | Combined web server + consumer | ✅ YES |
| `consumer.py` | Standalone consumer (if separating services) | Optional |
| `storage.py` | Handles S3/R2/local file storage | ✅ YES |
| `schema.sql` | Creates TimescaleDB tables | ✅ YES |
| `templates/*.html` | Web UI templates | ✅ YES |

### 🛠️ Utilities

| File | Purpose | Usage |
|------|---------|-------|
| `status.py` | Check Redis & DB status | `python status.py` |
| `reset.py` | Clear all data | `python reset.py` |
| `healthcheck.py` | Comprehensive health check | `python healthcheck.py` |
| `selenium_producer.py` | Load testing tool | `python selenium_producer.py` |

### ⚙️ Configuration

| File | Purpose | Notes |
|------|---------|-------|
| `requirements.txt` | Python packages | Auto-installed by Render |
| `runtime.txt` | Python version | Specifies Python 3.12 |
| `render.yaml` | Render config | Optional (can use dashboard) |
| `.env` | Environment variables | **Never commit!** |

### 📚 Documentation

| File | Best For |
|------|----------|
| `QUICKSTART.md` | First-time deployment |
| `RENDER_DEPLOYMENT.md` | Detailed Render setup |
| `CLOUD_DEPLOYMENT.md` | Multi-cloud deployment |
| `DEPLOYMENT_OPTIONS.md` | Choosing deployment type |
| `PERFORMANCE.md` | Optimization tips |
| `README.md` | Complete overview |

---

## What Was Removed?

All **local-only** files were deleted:

❌ Deleted:
- `app_local_backup.py` - Local version backup
- `app_old_backup.py` - Old version backup
- `consumer_local_backup.py` - Local consumer backup
- `setup.ps1` / `setup.sh` - Local setup scripts
- `setup_local_producer.ps1` - Local producer setup
- `local.md` - Local development guide
- `LOCAL_PRODUCER_*.md` - Local producer docs
- `run_producer_local.*` - Local runner scripts
- `run.py` - Local runner
- `Makefile` - Local dev commands
- `index.html` - Duplicate dashboard
- `local_producer_config.env` - Local config
- `deletable.txt` - Cleanup guide (no longer needed)
- `S3_FIX.md` - Fixed in code
- `deploy.md` - Replaced by better guides

✅ Kept:
- `selenium_producer.py` - Still useful for load testing locally

---

## Quick Deploy Checklist

```bash
# 1. Ensure these files exist:
✅ app.py
✅ storage.py
✅ schema.sql
✅ requirements.txt
✅ runtime.txt
✅ templates/dashboard.html
✅ templates/upload.html

# 2. Push to GitHub
git add .
git commit -m "Clean cloud deployment"
git push

# 3. Configure Render
# Add environment variables (see QUICKSTART.md)

# 4. Deploy!
# Render auto-deploys on push
```

---

## Environment Variables Required

```env
# Required for cloud deployment
ENABLE_CONSUMER=true
STORAGE_MODE=s3
REDIS_URL=redis://...
PG_URI=postgresql://...
S3_ENDPOINT=https://...
S3_BUCKET=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_PUBLIC_BASE_URL=https://...
```

See `QUICKSTART.md` for complete list.

---

## File Size Summary

**Total Essential Files:** ~15 files  
**Lines of Code:** ~2,500 lines  
**Dependencies:** ~20 Python packages  
**Deployment Target:** Render (free tier compatible)

---

## Next Steps

1. **Read:** `QUICKSTART.md`
2. **Configure:** Environment variables
3. **Push:** To GitHub
4. **Deploy:** Render auto-deploys
5. **Test:** Upload a file!

**Everything is ready for cloud deployment!** 🚀

