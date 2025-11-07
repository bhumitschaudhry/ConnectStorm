## 🚀 Step 1: Setup External Services

### A. Setup Redis

#### Option 1: Redis Cloud

1. Sign up at https://redis.com/try-free/
2. Create a new database (Free 30MB plan)
3. Note down the connection string: `redis://default:password@host:port`

#### Option 2: Upstash

1. Sign up at https://upstash.com/
2. Create Redis database
3. Copy the Redis URL from dashboard

### B. Setup TimescaleDB

#### Option 1: Timescale Cloud

1. Sign up at https://www.timescale.com/
2. Create new service (free trial)
3. Note the PostgreSQL connection string
4. Connect to database and run `schema.sql`:
   ```bash
   psql "postgres://user:pass@host:5432/dbname?sslmode=require" -f schema.sql
   ```

#### Option 2: Supabase

1. Create project at https://supabase.com/
2. Go to SQL Editor and run `schema.sql` contents
3. Get connection string from Settings > Database

### C. Setup Object Storage

#### Option 1: AWS S3

1. Create S3 bucket
2. Create IAM user with S3 access
3. Generate access key and secret key
4. Note:
   - Bucket name
   - Region (e.g., `us-east-1`)
   - Access Key
   - Secret Key

#### Option 2: Cloudflare R2

1. Go to Cloudflare Dashboard > R2
2. Create bucket
3. Create API token with R2 access
4. Note:
   - Bucket name
   - Account ID
   - Endpoint: `https://[account-id].r2.cloudflarestorage.com`
   - Access Key ID
   - Secret Access Key

---

## 🚀 Step 2: Prepare Your Repository

### 1. Clone or Initialize Repository

```bash
git clone <your-repo-url>
cd file-storm
```

### 2. Create Sample Upload Files

Create some test files in the `files/` directory for Selenium producer:

```bash
mkdir -p files
echo "Test file 1" > files/test1.txt
echo "Test file 2" > files/test2.txt
curl -o files/sample.png https://via.placeholder.com/150
```

### 3. Create Environment Configuration

Create `.env` file locally for testing (DO NOT commit this):

```bash
# Flask Configuration
FLASK_PORT=8080
SECRET_KEY=your-secret-key-here

# Redis Configuration
REDIS_URL=redis://default:password@your-redis-host:6379

# PostgreSQL/TimescaleDB Configuration
PG_URI=postgres://user:password@host:5432/dbname?sslmode=require

# Storage Configuration
STORAGE_MODE=s3

# S3/R2 Configuration
S3_ENDPOINT=https://your-endpoint
S3_REGION=us-east-1
S3_BUCKET=your-bucket
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_PUBLIC_BASE_URL=https://your-bucket.s3.amazonaws.com

# Selenium Producer Configuration
PRODUCER_TARGET_BASE_URL=http://localhost:8080/upload
PRODUCER_FILES_DIR=files
PRODUCER_USERS=5
PRODUCER_REPEATS=2
PRODUCER_HEADLESS=true
```

### 4. Test Locally (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask app
python app.py

# In another terminal, run consumer
python consumer.py

# In another terminal, run producer (after adding files to files/)
python selenium_producer.py
```

### 5. Commit and Push to GitHub

```bash
git add .
git commit -m "Initial File-Storm setup"
git push origin main
```

---

## 🚀 Step 3: Deploy to Render

### 1. Connect GitHub Repository

1. Log in to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Render will detect `render.yaml`

### 2. Configure Environment Variables

For each service, add these environment variables in Render Dashboard:

#### Web Service (filestorm-web)

```
SECRET_KEY=<generate-random-string>
REDIS_URL=redis://default:password@your-redis-host:6379
PG_URI=postgres://user:pass@host:5432/dbname?sslmode=require
STORAGE_MODE=s3
S3_ENDPOINT=<your-s3-endpoint>
S3_REGION=us-east-1
S3_BUCKET=<your-bucket>
S3_ACCESS_KEY=<your-key>
S3_SECRET_KEY=<your-secret>
S3_PUBLIC_BASE_URL=<your-public-url>
```

#### Consumer Worker (filestorm-consumer)

```
REDIS_URL=redis://default:password@your-redis-host:6379
PG_URI=postgres://user:pass@host:5432/dbname?sslmode=require
STORAGE_MODE=s3
S3_ENDPOINT=<your-s3-endpoint>
S3_REGION=us-east-1
S3_BUCKET=<your-bucket>
S3_ACCESS_KEY=<your-key>
S3_SECRET_KEY=<your-secret>
S3_PUBLIC_BASE_URL=<your-public-url>
CONSUMER_BATCH_SIZE=10
CONSUMER_BLOCK_MS=5000
```

#### Producer Worker (filestorm-producer)

```
PRODUCER_TARGET_BASE_URL=https://filestorm-web.onrender.com/upload
PRODUCER_FILES_DIR=files
PRODUCER_USERS=5
PRODUCER_REPEATS=2
PRODUCER_HEADLESS=true
```

### 3. Deploy

1. Click "Apply" to deploy all services
2. Wait for builds to complete (5-10 minutes)
3. Check logs for each service

---

## 🚀 Step 4: Initialize Database

After deployment, run the schema SQL:

```bash
psql "postgres://user:pass@host:5432/dbname?sslmode=require" -f schema.sql
```

Or use a database GUI like:

- DBeaver
- TablePlus
- pgAdmin

---

## 🚀 Step 5: Verify Deployment

### 1. Check Web Service

Visit your Render URL: `https://filestorm-web.onrender.com`

- Should see homepage with links to Upload and Dashboard
- Test file upload manually

### 2. Check Dashboard

Visit: `https://filestorm-web.onrender.com/dashboard`

- Should see Redis count and TimescaleDB count updating
- Timer should be running

### 3. Check Logs

In Render Dashboard, check logs for each service:

1. **Web Service**: Should show Flask startup
2. **Consumer Worker**: Should show "Starting File-Storm Consumer Worker"
3. **Producer Worker**: Should show uploads happening

### 4. Monitor Metrics

- **Redis**: Queue should fill up, then drain as consumer processes
- **TimescaleDB**: Row count should increase
- **Processing Rate**: Should show records/second

---

## 🚀 Step 6: Configure Selenium Producer

### Update Producer URL

After web service is deployed, update producer environment variable:

```
PRODUCER_TARGET_BASE_URL=https://your-actual-render-url.onrender.com/upload
```

### Add Upload Files

The producer needs files in the `files/` directory. Options:

1. **Commit files to repository** (recommended for small files):

   ```bash
   git add files/
   git commit -m "Add test files"
   git push
   ```

2. **Use init script** in `render.yaml`:
   ```yaml
   buildCommand: |
     pip install -r requirements.txt
     mkdir -p files
     echo "test" > files/test.txt
   ```

---

## 🔧 Troubleshooting

### Web Service Won't Start

- Check `REDIS_URL` and `PG_URI` are correct
- Verify TimescaleDB schema is applied
- Check logs for Python errors

### Consumer Not Processing

- Verify Redis Stream exists: `XINFO STREAM filestorm:uploads`
- Check consumer group exists: `XINFO GROUPS filestorm:uploads`
- Verify S3 credentials are correct

### Selenium Producer Fails

- Ensure Chrome is installed (check `render.yaml` buildCommand)
- Use `PRODUCER_HEADLESS=true` for Render
- Verify `PRODUCER_TARGET_BASE_URL` is correct and accessible
- Check files exist in `files/` directory

### Database Connection Issues

- Verify connection string includes `?sslmode=require`
- Check TimescaleDB extension is enabled
- Ensure `file_events` table exists

---

## 📊 Monitoring

### Check Redis Stream Length

```bash
redis-cli -u $REDIS_URL XLEN filestorm:uploads
```

### Check TimescaleDB Records

```sql
SELECT COUNT(*) FROM file_events;
SELECT * FROM file_events ORDER BY event_time DESC LIMIT 10;
```

### View Processing Stats

```sql
SELECT * FROM file_events_hourly ORDER BY bucket DESC LIMIT 24;
```

---

## 🎯 Performance Tips

### For Render Free Tier

1. **Limit concurrent users**: Keep `PRODUCER_USERS=3-5`
2. **Batch size**: Use `CONSUMER_BATCH_SIZE=10-20`
3. **Sleep between uploads**: Prevents overwhelming free tier
4. **Monitor usage**: Free tier has 750 hours/month

### Scaling Up

To handle more load:

1. Upgrade Render plan to paid tier
2. Increase `PRODUCER_USERS` and `PRODUCER_REPEATS`
3. Deploy multiple consumer workers
4. Increase `CONSUMER_BATCH_SIZE`

---

## 🔐 Security Checklist

- [ ] Use strong, unique `SECRET_KEY`
- [ ] Enable SSL for Redis (`rediss://`)
- [ ] Use `sslmode=require` for PostgreSQL
- [ ] Restrict S3 bucket permissions
- [ ] Don't commit `.env` file
- [ ] Use Render's environment variables (not hardcoded)
- [ ] Enable CORS if needed for API access

---

## 📝 Useful Commands

### Local Development

```bash
# Start Flask
python app.py

# Start consumer
python consumer.py

# Run producer
python selenium_producer.py

# Check Redis
redis-cli -u $REDIS_URL XLEN filestorm:uploads

# Check Database
psql $PG_URI -c "SELECT COUNT(*) FROM file_events"
```

### Render CLI

```bash
# Install Render CLI
npm install -g @render/cli

# Deploy
render deploy

# View logs
render logs filestorm-web
render logs filestorm-consumer
render logs filestorm-producer
```

---

## 🆘 Support Resources

- **Render Docs**: https://render.com/docs
- **Redis Docs**: https://redis.io/docs
- **TimescaleDB Docs**: https://docs.timescale.com/
- **Selenium Docs**: https://www.selenium.dev/documentation/
- **Flask Docs**: https://flask.palletsprojects.com/

---

## ✅ Deployment Checklist

- [ ] Redis instance created and accessible
- [ ] TimescaleDB instance created
- [ ] `schema.sql` executed successfully
- [ ] S3/R2 bucket created with credentials
- [ ] Repository pushed to GitHub
- [ ] Test files added to `files/` directory
- [ ] Render Blueprint deployed
- [ ] All environment variables configured
- [ ] Web service accessible
- [ ] Dashboard showing metrics
- [ ] Consumer processing messages
- [ ] Producer uploading files
- [ ] Files appearing in S3/R2
- [ ] Records appearing in TimescaleDB

---

**Congratulations! 🎉 Your File-Storm system is now live!**
