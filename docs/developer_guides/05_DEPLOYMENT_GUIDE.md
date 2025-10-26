# 05: Deployment Guide - Vercel + Render

**Last Updated:** 2025-10-26

This guide covers deploying YX NEXUS using a hybrid architecture:
- **Frontend (AURA)**: Vercel (global CDN, instant serving)
- **Backend (NEXUS)**: Render (free tier with keepalive optimization)

---

## Overview

### Architecture Diagram

```
┌─────────────┐     HTTPS/WSS      ┌──────────────┐     ┌──────────────┐
│   Browser   │ ──────────────────> │ Render       │ ──> │ MongoDB      │
│             │                     │ Backend      │     │ Atlas        │
└─────────────┘                     │ (FastAPI)    │     └──────────────┘
       │                            └──────────────┘
       │                                    ▲
       │ HTTPS                              │
       ▼                                    │ Health Check
┌─────────────┐                            │ (Every 10min)
│   Vercel    │                     ┌──────────────┐
│   CDN       │                     │GitHub Actions│
│  (Static)   │                     │  (Keepalive) │
└─────────────┘                     └──────────────┘
```

### Component Responsibilities

**Vercel Frontend:**
- Serves static React build from global edge network
- No server-side logic (pure static files)
- Handles SPA routing via rewrites
- Connects directly to Render backend via HTTPS/WSS

**Render Backend:**
- Runs FastAPI application with WebSocket support
- Connects to MongoDB Atlas
- Handles LLM orchestration and tool execution
- Protected by CORS (only allows specific frontend origins)

**GitHub Actions (Keepalive):**
- Scheduled workflow pings backend health endpoint every 10 minutes
- Prevents Render free tier from sleeping after 15 minutes of inactivity
- Automatically runs from your GitHub repository (no external service needed)
- Can send notifications on failure (optional)

### Why This Architecture?

**Problem:**
- Render free tier spins down after 15 minutes of inactivity
- Cold start takes 20-30 seconds (poor UX)
- Both frontend and backend on Render = both suffer from cold starts

**Solution:**
- **Instant frontend**: Vercel CDN serves static files with <2s load time globally
- **Warm backend**: GitHub Actions keepalive prevents most cold starts
- **Cost-effective**: All services free tier (Vercel unlimited, Render 750 hours/month, GitHub Actions 2000 min/month)
- **Simple architecture**: No nginx reverse proxy needed, direct HTTPS/WSS connections

---

## Prerequisites

### Required Accounts

1. **Vercel Account** (free tier)
   - Sign up: https://vercel.com/signup
   - Install CLI: `pnpm add -g vercel`

2. **Render Account** (already exists)
   - Dashboard: https://dashboard.render.com
   - Ensure backend service is deployed and running

3. **GitHub Repository** (already exists)
   - Repository with push access for GitHub Actions workflow
   - Actions must be enabled (enabled by default)

4. **MongoDB Atlas** (already configured)
   - Ensure connection allows Render IP ranges

### Required Information

Before starting, gather:
- [ ] Render backend URL (e.g., `https://nexus-backend-xxx.onrender.com`)
- [ ] GitHub repository with push access
- [ ] MongoDB Atlas connection string

---

## Deployment Steps

### Step 1: Verify Backend Configuration (5 min)

**1.1. Check Backend URL**

Go to Render Dashboard > `nexus-backend` > Settings:
- Note the full URL (e.g., `https://nexus-backend-tp8m.onrender.com`)
- This will be used in Vercel environment variables

**1.2. Verify Health Endpoint**

Test the health endpoint:

```bash
curl https://nexus-backend-xxx.onrender.com/api/v1/health
```

Expected response:
```json
{"status": "ok", "dependencies": {"database": "ok"}}
```

If this fails, ensure:
- Backend service is running on Render
- MongoDB connection is configured correctly
- No firewall blocking the endpoint

**1.3. Update ALLOWED_ORIGINS (Important!)**

This step is crucial for CORS to work. You'll do this AFTER getting your Vercel domain, but prepare now:

1. Go to Render Dashboard > `nexus-backend` > Environment
2. Find `ALLOWED_ORIGINS` variable
3. You'll add your Vercel domain here (e.g., `https://your-app.vercel.app`)

**Note:** Don't update this yet - you'll do it in Step 4 after deploying to Vercel.

---

### Step 2: Setup GitHub Actions Keepalive (2 min)

**2.1. Verify Workflow File Exists**

The keepalive workflow should already exist in your repository:
```
.github/workflows/keepalive.yml
```

If not, it will be created when you commit the migration changes.

**2.2. Update Backend URL in Workflow**

Edit `.github/workflows/keepalive.yml` and replace the placeholder URL:

```yaml
# Find this line:
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://nexus-backend-tp8m.onrender.com/api/v1/health)

# Update with your actual Render backend URL from Step 1
```

**2.3. Push to GitHub and Enable Actions**

```bash
git add .github/workflows/keepalive.yml
git commit -m "feat: add GitHub Actions keepalive workflow"
git push
```

**2.4. Verify Workflow is Running**

1. Go to your GitHub repository
2. Click "Actions" tab
3. You should see "Backend Keepalive" workflow
4. It will run automatically every 10 minutes
5. You can also click "Run workflow" to test immediately

**Why GitHub Actions?**
- Completely free (2000 minutes/month, each run takes <1 minute)
- Integrated with your repository
- No external service needed
- Reliable and easy to monitor

**Alternative Options:**
If GitHub Actions doesn't work for you, see the "Alternative Keepalive Methods" section at the end of this guide.

---

### Step 3: Deploy Frontend to Vercel (10 min)

**3.1. Install Vercel CLI**

```bash
pnpm add -g vercel
```

**3.2. Login to Vercel**

```bash
vercel login
```

Follow the browser authentication flow.

**3.3. Deploy from Project Root**

```bash
cd /path/to/NEXUS
vercel
```

The CLI will ask:
- **Set up and deploy?** → Yes
- **Which scope?** → Your personal account or team
- **Link to existing project?** → No (first time) or Yes (redeployment)
- **What's your project's name?** → `yx-nexus` or your preferred name
- **In which directory is your code located?** → `./` (project root)

Vercel will detect `vercel.json` configuration automatically.

**3.4. Note Your Vercel Domain**

After deployment completes, note the URL:
```
✅ Deployed to production: https://yx-nexus.vercel.app
```

**3.5. Set Environment Variables in Vercel Dashboard**

1. Go to https://vercel.com/dashboard
2. Select your project (`yx-nexus`)
3. Settings > Environment Variables
4. Add these variables (use backend URL from Step 1):

| Variable | Value | Environment |
|----------|-------|-------------|
| `VITE_AURA_WS_URL` | `wss://nexus-backend-xxx.onrender.com/api/v1/ws` | Production, Preview |
| `VITE_AURA_API_URL` | `https://nexus-backend-xxx.onrender.com/api/v1` | Production, Preview |
| `VITE_AURA_ENV` | `production` | Production |
| `VITE_APP_NAME` | `AURA` | Production, Preview |

**Important:** 
- Use `wss://` (not `https://`) for WebSocket URL
- Use `https://` (not `http://`) for API URL
- Environment should be "Production" and optionally "Preview"

**3.6. Trigger Rebuild**

After adding environment variables:

```bash
vercel --prod
```

Or in Vercel Dashboard:
- Deployments tab > Latest deployment > ⋯ menu > Redeploy

**3.7. Verify Build Success**

Check build logs in Vercel Dashboard:
- Should complete in <3 minutes
- No errors about missing environment variables
- Console output should show: `NEXUS Configuration: { env: 'production', wsUrl: 'wss://...', apiUrl: 'https://...' }`

---

### Step 4: Update Render CORS Configuration (2 min)

Now that you have your Vercel domain, update backend CORS:

**4.1. Update ALLOWED_ORIGINS**

1. Go to Render Dashboard > `nexus-backend` > Environment
2. Find `ALLOWED_ORIGINS` variable
3. Click "Edit"
4. Add your Vercel domain to the comma-separated list:

```
https://yx-nexus.vercel.app,http://localhost:5173,http://127.0.0.1:5173
```

If you have a custom domain, add it too:
```
https://yx-nexus.vercel.app,https://app.yxnexus.com,http://localhost:5173,http://127.0.0.1:5173
```

5. Click "Save Changes"

**4.2. Verify Automatic Redeploy**

Render will automatically redeploy the backend with new CORS settings. Wait ~2-3 minutes for deployment to complete.

Check deployment status:
- Render Dashboard > `nexus-backend` > Events
- Should show "Deploy succeeded"

---

### Step 5: End-to-End Verification (5 min)

**5.1. Test Frontend Loading**

1. Open your Vercel URL: `https://yx-nexus.vercel.app`
2. Should load in <2 seconds
3. Check browser console for configuration:
   ```
   NEXUS Configuration: {
     env: "production",
     wsUrl: "wss://nexus-backend-xxx.onrender.com/api/v1/ws",
     apiUrl: "https://nexus-backend-xxx.onrender.com/api/v1"
   }
   ```

**5.2. Test WebSocket Connection**

1. Open browser DevTools > Network tab > WS filter
2. Should see WebSocket connection to `wss://nexus-backend-xxx.onrender.com/api/v1/ws`
3. Status: 101 Switching Protocols (success)

**5.3. Test Message Streaming**

1. Send a test message: "Hello, what's 2+2?"
2. Should see:
   - Message appears in chat
   - Streaming response from LLM
   - No CORS errors in console

**5.4. Test Tool Execution (Optional)**

1. Send: "Search the web for Vite documentation"
2. Should see:
   - Tool execution indicator
   - Search results returned
   - No errors

**5.5. Test SPA Routing**

1. Navigate to different pages (e.g., `/config`)
2. Refresh the page (F5)
3. Should **not** see 404 error (Vercel rewrites working)

---

## Optional: Manual Deployment via GitHub Actions

### Purpose

Manually trigger deployments to Render and/or Vercel from GitHub Actions UI, without pushing code.

**Use cases:**
- Redeploy after environment variable changes
- Force rebuild without code changes
- Deploy from a specific commit
- Test deployment pipeline

### Setup (One-time)

**Required Secrets:**

1. **RENDER_DEPLOY_HOOK_BACKEND**
   - Go to [Render Dashboard](https://dashboard.render.com) > `nexus-backend` > Settings > Deploy Hook
   - Copy webhook URL
   - GitHub repo > Settings > Secrets and variables > Actions > New secret
   - Name: `RENDER_DEPLOY_HOOK_BACKEND`, Value: webhook URL

2. **VERCEL_DEPLOY_HOOK**
   - Go to [Vercel Dashboard](https://vercel.com/dashboard) > Your project > Settings > Git > Deploy Hooks
   - Create hook for `main` branch
   - Copy webhook URL
   - GitHub repo > Settings > Secrets and variables > Actions > New secret
   - Name: `VERCEL_DEPLOY_HOOK`, Value: webhook URL

**Detailed instructions:** See `.github/workflows/README.md`

### Usage

1. Go to GitHub repo > **Actions** tab
2. Select **"Manual Deploy"** workflow (left sidebar)
3. Click **"Run workflow"** button
4. Choose deployment target:
   - `all` - Deploy both backend and frontend
   - `backend` - Deploy only backend (Render)
   - `frontend` - Deploy only frontend (Vercel)
5. Click **"Run workflow"**

**Deployment time:** 3-5 minutes

**Check status:**
- GitHub Actions: View workflow run logs
- Render: Dashboard > `nexus-backend` > Events
- Vercel: Dashboard > Your project > Deployments

---

## Troubleshooting

### Build Errors

#### "Missing environment variables"

**Symptom:** Vercel build fails with error about missing `VITE_AURA_WS_URL` or `VITE_AURA_API_URL`.

**Solution:**
1. Go to Vercel Dashboard > Settings > Environment Variables
2. Ensure variables are added with correct names (case-sensitive)
3. Ensure "Production" environment is selected
4. Trigger rebuild: `vercel --prod`

#### "pnpm: command not found"

**Symptom:** Vercel build fails because pnpm is not installed.

**Solution:**
1. Update `vercel.json` to use npm instead:
   ```json
   "installCommand": "cd aura && npm ci",
   "buildCommand": "cd aura && npm run build"
   ```
2. Or ensure Vercel detects pnpm (usually automatic if `pnpm-lock.yaml` exists)

---

### Connection Errors

#### CORS Error: "Origin not allowed"

**Symptom:** Browser console shows:
```
Access to XMLHttpRequest at 'https://nexus-backend-xxx.onrender.com/api/v1/config'
from origin 'https://yx-nexus.vercel.app' has been blocked by CORS policy
```

**Solution:**
1. Check Render Dashboard > `nexus-backend` > Environment > `ALLOWED_ORIGINS`
2. Ensure your Vercel domain is in the list
3. Ensure no typos (e.g., `http` vs `https`, trailing slashes)
4. Redeploy backend if changed

#### WebSocket Connection Failed

**Symptom:** DevTools Network tab shows WebSocket connection fails (status 400 or timeout).

**Solution:**
1. Verify backend URL in Vercel environment variables uses `wss://` (not `https://`)
2. Check backend logs in Render Dashboard for errors
3. Test WebSocket directly with `wscat`:
   ```bash
   npm install -g wscat
   wscat -c "wss://nexus-backend-xxx.onrender.com/api/v1/ws"
   ```
4. If timeout, check if backend is sleeping (wait for keepalive to wake it, or trigger GitHub Actions workflow manually)

#### "Backend URLs not configured" Warning

**Symptom:** Frontend loads but console shows: `⚠️ Backend URLs not configured. WebSocket connection will fail.`

**Solution:**
1. This means environment variables were not set during build
2. Vercel Dashboard > Settings > Environment Variables
3. Add `VITE_AURA_WS_URL` and `VITE_AURA_API_URL`
4. Redeploy: `vercel --prod`

---

### Performance Issues

#### Frontend Loads Slowly

**Symptom:** Vercel frontend takes >5 seconds to load.

**Diagnosis:**
1. Test from multiple locations: https://www.webpagetest.org/
2. Check if specific region is slow

**Solution:**
- Vercel CDN should be instant globally (<2s)
- If slow everywhere, check Vercel Analytics for issues
- Ensure `vercel.json` has correct cache headers for `/assets/`

#### Backend Cold Start

**Symptom:** First request takes 20-30 seconds after idle period.

**Expected Behavior:**
- Render free tier **will** sleep after 15 minutes without requests
- Cold start is unavoidable on free tier
- GitHub Actions keepalive keeps it warm most of the time

**Solution:**
1. Verify GitHub Actions workflow is running (check Actions tab in repository)
2. Check workflow run history for failed pings
3. If still sleeping, consider upgrading Render plan ($7/month for always-on) or try alternative keepalive methods

---

### SPA Routing Issues

#### 404 on Page Refresh

**Symptom:** Navigating to `/config` works, but refreshing the page shows 404.

**Solution:**
1. Check `vercel.json` has rewrites configuration:
   ```json
   "rewrites": [
     { "source": "/(.*)", "destination": "/index.html" }
   ]
   ```
2. Redeploy if missing

---

## Monitoring

### Vercel Analytics

**Access:** Vercel Dashboard > Project > Analytics

**Key Metrics:**
- Page load time (should be <2s globally)
- Error rate (should be near 0%)
- Geographic distribution

**Alarms:**
- Set up Slack/Discord webhook for deployment failures
- Vercel Dashboard > Project > Settings > Notifications

### Render Logs

**Access:** Render Dashboard > `nexus-backend` > Logs

**What to Monitor:**
- WebSocket connection logs
- Tool execution errors
- Database connection issues

**Useful Log Filters:**
```
# WebSocket connections
/ws

# Errors only
ERROR

# Health checks (confirm keepalive working)
/health
```

### GitHub Actions Status

**Access:** GitHub Repository > Actions tab > Backend Keepalive workflow

**Key Metrics:**
- Workflow run success rate (should be >99%)
- Average response time in logs (should be <1s when warm, <20s after cold start)
- Failed runs (investigate if >5% in a day)

**Notifications:**
- GitHub sends email notifications on workflow failures
- Can integrate with Slack/Discord via webhooks (optional)
- View detailed logs for each run

---

## Rollback Procedure

### Rollback Frontend (Instant)

**If new Vercel deployment breaks:**

1. Vercel Dashboard > Project > Deployments
2. Find previous working deployment
3. Click ⋯ menu > "Promote to Production"
4. Takes effect immediately (no rebuild needed)

**Or via CLI:**
```bash
vercel rollback https://yx-nexus-xyz123.vercel.app
```

### Rollback Backend CORS

**If CORS changes break existing Render frontend:**

1. Render Dashboard > `nexus-backend` > Environment
2. Find `ALLOWED_ORIGINS`
3. Remove Vercel domain from list
4. Click "Save Changes" (triggers automatic redeploy)

### Emergency: Revert All Changes

**If complete rollback needed:**

1. **Frontend:** Keep Render frontend service running (leave as-is)
2. **Backend:** Revert CORS to original value (remove Vercel domains)
3. **Vercel:** Delete Vercel deployment or set to draft mode

---

## Custom Domain Setup (Optional)

### Frontend Custom Domain

**Prerequisites:**
- Own a domain (e.g., `aura.yxnexus.com`)
- Access to DNS settings

**Steps:**

1. Vercel Dashboard > Project > Settings > Domains
2. Add domain: `aura.yxnexus.com`
3. Vercel provides DNS records (A/AAAA or CNAME)
4. Add records to your DNS provider
5. Wait for propagation (5-60 minutes)
6. Vercel automatically provisions SSL certificate

**Update Backend CORS:**
- Add custom domain to `ALLOWED_ORIGINS` in Render
- Remove Vercel default domain if desired

### Backend Custom Domain

**Prerequisites:**
- Own a domain (e.g., `api.yxnexus.com`)
- Render paid plan ($7/month minimum)

**Steps:**

1. Render Dashboard > `nexus-backend` > Settings > Custom Domains
2. Add domain: `api.yxnexus.com`
3. Add CNAME record to DNS: `api.yxnexus.com` → `nexus-backend-xxx.onrender.com`
4. Wait for verification
5. Update Vercel environment variables to use custom domain

**Benefits:**
- Branded URLs
- URL doesn't change if Render redeploys service
- Professional appearance

---

## Cost Breakdown

| Service | Plan | Monthly Cost | Limits |
|---------|------|--------------|--------|
| **Vercel** | Hobby (Free) | $0 | 100GB bandwidth, unlimited requests |
| **Render** | Free | $0 | 750 hours/month (enough for 1 service) |
| **GitHub Actions** | Free | $0 | 2000 minutes/month (keepalive uses <20 min/month) |
| **MongoDB Atlas** | Free | $0 | 512MB storage |
| **Total** | | **$0/month** | |

**Upgrade Paths:**

- **Vercel Pro** ($20/month): Analytics, team features, higher bandwidth
- **Render Starter** ($7/month): Always-on service (no cold starts)
- **MongoDB Atlas M10** ($57/month): Production-grade performance

---

## Maintenance Tasks

### Monthly Checklist

- [ ] Check Vercel Analytics for performance issues
- [ ] Review Render logs for recurring errors
- [ ] Verify GitHub Actions keepalive workflow is running (check Actions tab)
- [ ] Test full deployment flow with staging branch

### Quarterly Checklist

- [ ] Review and update `ALLOWED_ORIGINS` (remove old domains)
- [ ] Test rollback procedure (ensure process is fresh in memory)
- [ ] Review costs and consider upgrades if traffic increased

---

## Alternative Keepalive Methods

If GitHub Actions is not suitable for your setup, here are other free options to keep the Render backend warm:

### Option 1: UptimeRobot (External Service)

**Best for:** Users who prefer external monitoring services or can't access GitHub.

**Setup:**
1. Sign up: https://uptimerobot.com/signUp (free tier)
2. Create HTTP monitor:
   - URL: `https://nexus-backend-xxx.onrender.com/api/v1/health`
   - Interval: 10 minutes
   - Alert email: your email
3. Verify monitor shows "Up" status

**Pros:** Email alerts, separate from code repository  
**Cons:** External service dependency, may be blocked in some regions

---

### Option 2: Cron-job.org (External Service)

**Best for:** Simple cron job without email account creation hassle.

**Setup:**
1. Sign up: https://cron-job.org/en/ (free tier)
2. Create new cron job:
   - URL: `https://nexus-backend-xxx.onrender.com/api/v1/health`
   - Schedule: `*/10 * * * *` (every 10 minutes)
3. Enable notification on failure

**Pros:** Easy setup, reliable  
**Cons:** External service dependency

---

### Option 3: Self-Hosted Script

**Best for:** Users with a server or always-on computer.

Use the script in `scripts/keepalive.sh`:

```bash
# Make executable
chmod +x scripts/keepalive.sh

# Add to crontab (every 10 minutes)
crontab -e
# Add line:
*/10 * * * * /path/to/NEXUS/scripts/keepalive.sh
```

**Pros:** Full control, no external dependencies  
**Cons:** Requires always-on machine

---

### Option 4: Render Cron Jobs (Requires Render Setup)

**Best for:** Users who want everything on Render platform.

Add to `render.yaml`:

```yaml
- name: nexus-keepalive
  type: cron
  env: docker
  schedule: "*/10 * * * *"
  dockerCommand: "curl -f https://nexus-backend-tp8m.onrender.com/api/v1/health || exit 1"
```

**Pros:** Integrated with Render  
**Cons:** Requires cron job service (may have limits on free tier)

---

## Additional Resources

**Official Documentation:**
- [Vercel Configuration](https://vercel.com/docs/projects/project-configuration)
- [Render Deployment](https://render.com/docs/deploy-fastapi)
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)

**Internal Documentation:**
- `01_SETUP_AND_RUN.md` - Local development setup
- `docs/knowledge_base/technical_references/environment_configuration.md` - Environment variables reference
- `docs/learn/2025-09-11-render-vite-ws-nginx.md` - Previous Render architecture lessons

**External Tools:**
- [Webpage Test](https://www.webpagetest.org/) - Test global load times
- [wscat](https://www.npmjs.com/package/wscat) - WebSocket debugging CLI

---

## Support

**Issues or Questions?**

1. Check troubleshooting section above
2. Review Render/Vercel status pages for outages
3. Check GitHub Issues for similar problems
4. Create new issue with deployment logs and error messages

**Emergency Contact:**
- Render Support: https://render.com/support
- Vercel Support: https://vercel.com/support

---

*Last verified: 2025-10-26*
