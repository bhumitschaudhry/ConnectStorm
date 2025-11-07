# ⚡ File-Storm Quick Start Guide

Get File-Storm running in 5 minutes!

---

## 🚀 Local Development (5 steps)

### Step 1: Install Dependencies

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
source venv/bin/activate
```

**Windows:**
```powershell
.\setup.ps1
.\venv\Scripts\Activate.ps1
```

**Or manually:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
.\venv\Scripts\Activate.ps1  # Windows

pip install -r requirements.txt
```

---

### Step 2: Configure Environment

Copy and edit the environment file:

```bash
cp env.example .env
```

Edit `.env` with your credentials:

```bash
# Minimum required for local testing with local storage:
REDIS_URL=redis://localhost:6379
PG_URI=postgres://user:pass@localhost:5432/filestorm
STORAGE_MODE=local
SECRET_KEY=your-secret-key-here
```

---

### Step 3: Setup Database

Run the TimescaleDB schema:

```bash
psql $PG_URI -f schema.sql
```

Or if using psql directly:
```bash
psql -h localhost -U postgres -d filestorm -f schema.sql
```

---

### Step 4: Run Health Check

Verify everything is configured correctly:

```bash
python healthcheck.py
```

This will check:
- ✓ Python packages installed
- ✓ Environment variables set
- ✓ Redis connection
- ✓ PostgreSQL/TimescaleDB connection
- ✓ Storage configuration
- ✓ Selenium setup

---

### Step 5: Start Services

**Option A: Individual terminals (recommended for development)**

Terminal 1 - Flask Web:
```bash
python app.py
```

Terminal 2 - Consumer Worker:
```bash
python consumer.py
```

Terminal 3 - Selenium Producer:
```bash
python selenium_producer.py
```

**Option B: All at once with multiprocessing**
```bash
python run.py
```

**Option C: Using Make (Linux/Mac)**
```bash
make run-web      # Terminal 1
make run-consumer # Terminal 2
make run-producer # Terminal 3
```

---

## 🌐 Access the Application

Once running, visit:

- **Homepage**: http://localhost:8080
- **Upload Page**: http://localhost:8080/upload
- **Dashboard**: http://localhost:8080/dashboard
- **API Counts**: http://localhost:8080/api/counts
- **Health Check**: http://localhost:8080/health

---

## 📊 Monitor Activity

### Watch Dashboard
Open http://localhost:8080/dashboard and watch:
- Redis queue size (should increase when producer runs)
- TimescaleDB count (should increase as consumer processes)
- Processing rate (records/second)

### Check Redis Stream
```bash
redis-cli -u $REDIS_URL XLEN filestorm:uploads
```

### Check Database Records
```bash
psql $PG_URI -c "SELECT COUNT(*) FROM file_events;"
psql $PG_URI -c "SELECT * FROM file_events ORDER BY event_time DESC LIMIT 10;"
```

---

## 🧪 Test the System

### Manual Upload Test
1. Visit http://localhost:8080/upload
2. Select a file from your computer
3. Enter an uploader ID (optional): `test_user`
4. Click "Upload File"
5. Check dashboard for updated counts

### Automated Upload Test
```bash
# Make sure you have files in the files/ directory
python selenium_producer.py
```

This will:
- Spawn 5 concurrent browser sessions (headless)
- Each uploads 2 random files from `files/` directory
- Shows real-time progress
- Displays summary at the end

---

## 🔧 Configuration Tips

### Adjust Selenium Behavior

Edit `.env`:
```bash
PRODUCER_USERS=3          # Number of concurrent users
PRODUCER_REPEATS=5        # Uploads per user
PRODUCER_HEADLESS=false   # Show browser (for debugging)
```

### Adjust Consumer Performance

Edit `.env`:
```bash
CONSUMER_BATCH_SIZE=20    # Process 20 messages at once
CONSUMER_BLOCK_MS=2000    # Wait 2s for new messages
```

### Use Local Storage (for testing)

Edit `.env`:
```bash
STORAGE_MODE=local
LOCAL_STORAGE_DIR=/tmp/filestorm_storage
```

Files will be stored locally instead of S3/R2.

---

## 🐛 Troubleshooting

### "Redis connection failed"
- Ensure Redis is running: `redis-server`
- Check REDIS_URL in .env
- Test: `redis-cli ping`

### "Database connection failed"
- Ensure PostgreSQL is running
- Check PG_URI in .env
- Verify database exists: `psql $PG_URI -c "SELECT 1;"`

### "Schema not found"
- Run: `psql $PG_URI -f schema.sql`
- Check if table exists: `psql $PG_URI -c "\dt"`

### "Selenium can't find files"
- Add files to `files/` directory
- Check PRODUCER_FILES_DIR in .env
- Verify files exist: `ls files/`

### "Chrome driver not found"
- Install Chrome browser
- Selenium will auto-download chromedriver
- Or manually: https://chromedriver.chromium.org/

### "No module named 'flask'"
- Activate virtual environment
- Install dependencies: `pip install -r requirements.txt`

---

## ☁️ Deploy to Cloud

Ready to deploy to Render? See **[deploy.md](deploy.md)** for complete instructions.

Quick summary:
1. Push code to GitHub
2. Setup managed Redis (Redis Cloud / Upstash)
3. Setup TimescaleDB (Timescale Cloud / Supabase)
4. Setup S3 or R2
5. Deploy to Render using `render.yaml`
6. Configure environment variables
7. Done! 🎉

---

## 📚 Next Steps

### Learn More
- Read [README.md](README.md) for architecture details
- Read [deploy.md](deploy.md) for production deployment
- Check `render.yaml` for service configuration

### Customize
- Modify `templates/upload.html` for custom UI
- Edit `templates/dashboard.html` for custom metrics
- Add authentication in `app.py`
- Implement file validation
- Add more API endpoints

### Scale Up
- Deploy multiple consumer workers
- Increase batch sizes
- Add load balancer
- Enable auto-scaling on Render

---

## 🆘 Getting Help

If you run into issues:

1. **Run health check**: `python healthcheck.py`
2. **Check logs**: Look at console output for errors
3. **Verify config**: Ensure `.env` is correct
4. **Test connections**: Use redis-cli and psql
5. **Read docs**: See README.md and deploy.md

---

## ✅ Success Checklist

- [ ] Dependencies installed
- [ ] `.env` file configured
- [ ] Redis accessible
- [ ] PostgreSQL/TimescaleDB accessible
- [ ] Schema applied (file_events table exists)
- [ ] Files added to `files/` directory
- [ ] Flask web server starts
- [ ] Can access http://localhost:8080
- [ ] Dashboard shows metrics
- [ ] Manual upload works
- [ ] Consumer processes messages
- [ ] Producer runs successfully
- [ ] Records appear in database

---

**You're all set! 🎉**

Start uploading files and watch the distributed system in action!

