# 🔄 Render Auto-Deploy Guide

## ✅ Yes, Render Will Auto-Deploy!

**When you push to GitHub, Render automatically:**
1. ✅ Detects the push
2. ✅ Pulls the latest code
3. ✅ Runs the build command
4. ✅ Restarts your service
5. ✅ Your app is live with new changes!

---

## 🔍 How It Works

### Default Behavior

Render **automatically deploys** when:
- ✅ You push to the **main/master branch** (if that's your connected branch)
- ✅ You push to the **specific branch** you connected in Render dashboard

### Setup Check

1. **Go to Render Dashboard:**
   - https://dashboard.render.com
   - Click on your service

2. **Check "Settings" → "Build & Deploy":**
   - **Auto-Deploy:** Should be set to **"Yes"**
   - **Branch:** Should be your main branch (usually `main` or `master`)

3. **If Auto-Deploy is disabled:**
   - Toggle it **ON**
   - Save changes

---

## 📋 What Happens When You Push

### Step-by-Step Process

```bash
# 1. You push to GitHub
git add .
git commit -m "Update to ConnectStorm"
git push origin main

# 2. Render detects the push (within seconds)
# 3. Render starts build process:
#    - Clones your repo
#    - Runs: pip install -r requirements.txt
#    - Runs: python app.py (your start command)

# 4. Service restarts with new code
# 5. Your app is live! 🎉
```

### Timeline

- **Detection:** 10-30 seconds after push
- **Build:** 1-3 minutes (depends on dependencies)
- **Deploy:** 30-60 seconds
- **Total:** ~2-5 minutes from push to live

---

## ⚙️ Configuration (render.yaml)

Your `render.yaml` is configured for auto-deploy:

```yaml
services:
  - type: web
    name: connectstorm-web
    buildCommand: pip install -r requirements.txt
    startCommand: python app.py  # ✅ Correct!
    envVars:
      - key: ENABLE_CONSUMER
        value: "true"  # ✅ Added!
      # ... other vars
```

**What this does:**
- ✅ Uses `render.yaml` for configuration
- ✅ Auto-deploys when you push
- ✅ Sets `ENABLE_CONSUMER=true` automatically

---

## 🧪 Testing Auto-Deploy

### Test It Now:

```bash
# 1. Make a small change (add a comment)
echo "# Test auto-deploy" >> app.py

# 2. Commit and push
git add app.py
git commit -m "Test auto-deploy"
git push

# 3. Watch Render Dashboard
# Go to: https://dashboard.render.com → Your service → "Events"
# You should see: "New commit detected" → "Build started" → "Deploy started"
```

### Monitor Deployment:

1. **Render Dashboard:**
   - Go to your service
   - Click **"Events"** tab
   - Watch the build progress

2. **Logs:**
   - Click **"Logs"** tab
   - See real-time build and deployment logs

---

## 🔧 Manual Deploy (If Needed)

If auto-deploy is disabled, you can manually deploy:

1. **Render Dashboard:**
   - Go to your service
   - Click **"Manual Deploy"** button
   - Select branch and click **"Deploy latest commit"**

---

## ⚠️ Important Notes

### Environment Variables

**Variables marked `sync: false` in render.yaml:**
- ✅ Must be set **manually in Render dashboard**
- ✅ Won't be overwritten by render.yaml
- ✅ Safe for secrets (REDIS_URL, PG_URI, etc.)

**To set them:**
1. Go to Render Dashboard → Your service
2. Click **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Add each variable:
   - `REDIS_URL` = `your-redis-url`
   - `PG_URI` = `your-postgres-url`
   - `S3_ACCESS_KEY` = `your-key`
   - etc.

### First Deploy

**On first deploy, you must:**
1. ✅ Set all environment variables (secrets)
2. ✅ Verify `ENABLE_CONSUMER=true` is set
3. ✅ Check that build completes successfully
4. ✅ Test the `/health` endpoint

---

## 🚨 Troubleshooting

### Auto-deploy not working?

**Check:**
1. **GitHub Connection:**
   - Render Dashboard → Settings → "GitHub"
   - Verify repo is connected

2. **Branch:**
   - Settings → Build & Deploy
   - Confirm branch matches your push branch

3. **Auto-Deploy:**
   - Settings → Build & Deploy
   - Ensure "Auto-Deploy" is **ON**

### Build fails?

**Check logs:**
- Render Dashboard → Logs tab
- Look for error messages
- Common issues:
  - Missing dependencies in `requirements.txt`
  - Python version mismatch
  - Environment variables not set

### Service not starting?

**Check:**
1. **Start command:**
   - Should be: `python app.py`
   - Not: `gunicorn` (we don't use that anymore)

2. **Port:**
   - App should use `$PORT` or `8080`
   - Render sets `$PORT` automatically

3. **Health check:**
   - `/health` endpoint must return 200 OK
   - Check logs for errors

---

## 📊 Deployment Status

### Check Deployment Status:

**Render Dashboard:**
- ✅ **Live:** Green dot = service running
- 🔄 **Deploying:** Blue dot = deploying
- ❌ **Failed:** Red dot = build/deploy failed

**Events Tab:**
- Shows all deployments
- Shows build/deploy times
- Shows commit messages

---

## 🎯 Best Practices

### 1. Test Before Pushing

```bash
# Test locally first
python app.py
# Check: http://localhost:8080/health
```

### 2. Use Meaningful Commits

```bash
git commit -m "Add ConnectStorm branding"
git commit -m "Fix consumer connection pooling"
```

### 3. Monitor First Deploy

After pushing:
- ✅ Watch Render logs
- ✅ Check health endpoint
- ✅ Test upload functionality

### 4. Keep Secrets Safe

- ✅ Never commit `.env` file
- ✅ Use `sync: false` in render.yaml for secrets
- ✅ Set secrets in Render dashboard only

---

## ✅ Summary

**Yes, Render auto-deploys when you push!**

**Process:**
1. Push to GitHub
2. Render detects push (seconds)
3. Build starts automatically
4. Deploy completes (2-5 minutes)
5. Your app is live!

**Your render.yaml is ready:**
- ✅ Correct start command: `python app.py`
- ✅ `ENABLE_CONSUMER=true` set
- ✅ Auto-deploy enabled by default

**Just push and watch it deploy!** 🚀

---

## 🔗 Quick Links

- **Render Dashboard:** https://dashboard.render.com
- **Your Service:** Check your dashboard for the URL
- **Logs:** Dashboard → Your service → Logs tab
- **Events:** Dashboard → Your service → Events tab

---

**That's it! Every time you `git push`, Render will automatically deploy your changes!** ✨

