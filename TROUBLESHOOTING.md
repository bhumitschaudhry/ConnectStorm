# 🔧 Troubleshooting: Messages Not Moving to TimescaleDB

## Common Issues & Solutions

### 1. ❌ Consumer Not Enabled

**Symptoms:**
- Messages stuck in Redis
- No consumer logs
- Dashboard shows Redis count but not TimescaleDB count

**Check:**
```bash
# Look for this in Render logs:
⚠ Consumer is DISABLED!
```

**Fix:**
1. Go to Render Dashboard → Your service → **Environment**
2. Add/update: `ENABLE_CONSUMER=true`
3. Redeploy (or wait for auto-deploy)

---

### 2. ❌ Database Connection Failed

**Symptoms:**
- Consumer logs show: `✗ Failed to initialize connection pool`
- No database records

**Check Render Logs:**
```
✗ Failed to initialize connection pool: ...
```

**Fix:**
1. Verify `PG_URI` is set correctly in Render
2. Check database credentials
3. Verify database is accessible (not paused)
4. Check if `sslmode=require` is in PG_URI

**Test:**
```bash
# Run diagnostic
python diagnose_consumer.py
```

---

### 3. ❌ Consumer Group Not Created

**Symptoms:**
- Consumer logs show: `⚠️ Consumer group not found`
- Messages not being read

**Fix:**
- Consumer should auto-create the group
- Check logs for: `✓ Created consumer group 'connectstorm_group'`

**Manual Fix:**
```bash
# Connect to Redis
redis-cli -u YOUR_REDIS_URL

# Create group manually
XGROUP CREATE connectstorm:uploads connectstorm_group 0 MKSTREAM
```

---

### 4. ❌ Database Insert Errors

**Symptoms:**
- Consumer processes messages but no DB records
- Logs show: `✗ Batch insert error`

**Check:**
1. Look for error messages in Render logs
2. Verify table exists: `file_events`
3. Check database permissions

**Fix:**
```sql
-- Verify table exists
SELECT * FROM file_events LIMIT 1;

-- If table doesn't exist, run:
-- psql YOUR_PG_URI -f schema.sql
```

---

### 5. ❌ Port Configuration Issue

**Symptoms:**
- App not starting
- Connection refused errors

**Fix:**
- Render sets `$PORT` automatically
- App now uses: `os.getenv('PORT', os.getenv('FLASK_PORT', 8080))`
- No action needed if using latest code

---

## Diagnostic Steps

### Step 1: Check Render Logs

1. Go to Render Dashboard
2. Click your service
3. Click **"Logs"** tab
4. Look for:

**✅ Good signs:**
```
✓ Database connection pool initialized and tested
✓ Consumer group 'connectstorm_group' already exists
🚀 Consumer worker started in background
📥 Consumer: Processing X messages
✓ Batch insert: X records inserted to database
```

**❌ Bad signs:**
```
✗ Failed to initialize connection pool
⚠ Consumer is DISABLED!
✗ Batch insert error
⚠ Consumer group not found
```

### Step 2: Run Diagnostic Script

```bash
# Locally or on Render shell
python diagnose_consumer.py
```

This will check:
- ENABLE_CONSUMER setting
- Redis connection
- Database connection
- Pending messages
- Consumer group status

### Step 3: Check Environment Variables

**Required in Render Dashboard:**

```
ENABLE_CONSUMER=true          ← CRITICAL!
STORAGE_MODE=s3
REDIS_URL=redis://...
PG_URI=postgresql://...
S3_ENDPOINT=https://...
S3_BUCKET=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_PUBLIC_BASE_URL=https://...
```

### Step 4: Test Health Endpoint

```bash
curl https://your-app.onrender.com/health
```

Should return:
```json
{
  "status": "healthy",
  "consumer_enabled": true,
  "consumer_running": true,
  "timestamp": "..."
}
```

If `consumer_enabled` or `consumer_running` is `false`, consumer is not working!

---

## Quick Fixes

### Fix 1: Enable Consumer

```bash
# In Render Dashboard → Environment:
ENABLE_CONSUMER=true
```

### Fix 2: Reset Redis Queue

```bash
# If messages are stuck:
python reset.py
# Type: RESET
```

### Fix 3: Verify Database Schema

```bash
# Connect to database
psql YOUR_PG_URI

# Check table
\d file_events

# If missing, create:
\i schema.sql
```

### Fix 4: Check Consumer Logs

```bash
# In Render Dashboard → Logs
# Filter for: "Consumer"
# Look for processing messages
```

---

## Debugging Checklist

- [ ] `ENABLE_CONSUMER=true` is set in Render
- [ ] Database connection pool initializes successfully
- [ ] Consumer group exists or is created
- [ ] Consumer worker thread starts
- [ ] Messages are being read from Redis
- [ ] Database inserts are successful
- [ ] Messages are acknowledged after insert

---

## Still Not Working?

### 1. Check Full Logs

In Render Dashboard → Logs, look for:
- Error messages
- Stack traces
- Warning messages

### 2. Test Locally

```bash
# Set environment variables
export ENABLE_CONSUMER=true
export REDIS_URL=...
export PG_URI=...

# Run app
python app.py

# Watch logs for consumer activity
```

### 3. Verify Database

```bash
# Check if records are being inserted
psql YOUR_PG_URI -c "SELECT COUNT(*) FROM file_events;"

# Check recent records
psql YOUR_PG_URI -c "SELECT * FROM file_events ORDER BY event_time DESC LIMIT 5;"
```

### 4. Check Redis

```bash
# Check queue length
redis-cli -u YOUR_REDIS_URL XLEN connectstorm:uploads

# Check consumer group
redis-cli -u YOUR_REDIS_URL XINFO GROUPS connectstorm:uploads
```

---

## Common Error Messages

### "Consumer is DISABLED"
**Fix:** Set `ENABLE_CONSUMER=true` in Render

### "Failed to initialize connection pool"
**Fix:** Check `PG_URI` is correct and database is accessible

### "Consumer group not found"
**Fix:** Consumer should auto-create, but check Redis permissions

### "Batch insert error"
**Fix:** Check database schema exists and permissions are correct

### "No messages returned from consumer group"
**Fix:** Check if messages exist in stream and consumer group is correct

---

## Success Indicators

When everything works, you'll see:

```
✓ Database connection pool initialized and tested
✓ Consumer group 'connectstorm_group' already exists
🚀 Consumer worker started in background
📥 Consumer: Processing 5 messages
📊 Consumer: Attempting to insert 5 records to database
✓ Batch insert: 5 records inserted to database
✓ Consumer: Acknowledged 5 messages
✓ Consumer: 5 processed (total: 5)
```

---

## Need More Help?

1. **Check Render logs** - Most errors are visible there
2. **Run diagnostic script** - `python diagnose_consumer.py`
3. **Check health endpoint** - `curl /health`
4. **Verify environment variables** - All required vars set
5. **Test locally** - Reproduce issue locally

---

**Most common fix:** Set `ENABLE_CONSUMER=true` in Render Dashboard! 🔧

