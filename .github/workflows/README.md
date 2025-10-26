# GitHub Actions Workflows

## Overview

This directory contains automated workflows for the NEXUS project:

1. **`keepalive.yml`** - Backend keepalive (prevents Render cold starts)
2. **`manual_deploy.yml`** - Manual deployment trigger for Render + Vercel

---

## Keepalive Workflow

### Purpose
Pings Render backend every 10 minutes to prevent free tier cold starts.

### Configuration
See `.github/workflows/README.md` (created earlier) for email notification setup.

---

## Manual Deploy Workflow

### Purpose
Manually trigger deployments to Render (backend) and/or Vercel (frontend) from GitHub Actions UI.

### Usage

1. Go to GitHub repository > **Actions** tab
2. Select **"Manual Deploy"** workflow
3. Click **"Run workflow"** button
4. Choose deployment target:
   - **all** - Deploy both backend and frontend
   - **backend** - Deploy only backend (Render)
   - **frontend** - Deploy only frontend (Vercel)
5. Click **"Run workflow"** to start

### Required GitHub Secrets

You must configure these secrets in your GitHub repository:

#### 1. **RENDER_DEPLOY_HOOK_BACKEND**

**What:** Render backend deploy hook URL  
**Where to get it:**
1. Go to [Render Dashboard](https://dashboard.render.com)
2. Select `nexus-backend` service
3. Settings > **Deploy Hook**
4. Copy the webhook URL (looks like: `https://api.render.com/deploy/srv-xxx?key=yyy`)

**How to add:**
1. GitHub repo > Settings > Secrets and variables > Actions
2. Click **New repository secret**
3. Name: `RENDER_DEPLOY_HOOK_BACKEND`
4. Value: Paste the Render deploy hook URL
5. Click **Add secret**

---

#### 2. **VERCEL_DEPLOY_HOOK**

**What:** Vercel frontend deploy hook URL  
**Where to get it:**
1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Select your project (`nexus` or `yx-nexus`)
3. Settings > **Git** > **Deploy Hooks**
4. Create a new deploy hook:
   - Name: `GitHub Actions Manual Deploy`
   - Branch: `main` (or your production branch)
5. Click **Create Hook**
6. Copy the webhook URL (looks like: `https://api.vercel.com/v1/integrations/deploy/xxx/yyy`)

**How to add:**
1. GitHub repo > Settings > Secrets and variables > Actions
2. Click **New repository secret**
3. Name: `VERCEL_DEPLOY_HOOK`
4. Value: Paste the Vercel deploy hook URL
5. Click **Add secret**

---

#### 3. **Optional: NOTIFICATION_EMAIL & NOTIFICATION_EMAIL_PASSWORD**

For custom email notifications on keepalive failures (see keepalive workflow README).

---

## Workflow Features

### Error Handling
- ✅ HTTP status code validation
- ✅ Clear success/failure messages
- ✅ Exits with error if deployment fails

### Deployment Summary
After workflow completes, check the **Summary** tab for:
- Links to Render/Vercel dashboards
- Estimated deployment time
- Service-specific information

### Example Output

**Successful deployment:**
```
🚀 Triggering backend deployment to Render...
✅ Backend deployment triggered successfully

🚀 Triggering frontend deployment to Vercel...
✅ Frontend deployment triggered successfully
```

**Failed deployment:**
```
🚀 Triggering backend deployment to Render...
❌ Backend deployment failed with HTTP 401
```

---

## Deployment Time Estimates

| Service | Platform | Typical Duration |
|---------|----------|------------------|
| Backend | Render | 3-5 minutes |
| Frontend | Vercel | 2-3 minutes |
| Both | Render + Vercel | 3-5 minutes (parallel) |

---

## When to Use Manual Deploy

**Use this workflow when:**
- ✅ You want to deploy without pushing code
- ✅ You need to redeploy after environment variable changes
- ✅ You want to trigger deployments from a specific commit
- ✅ You need to test deployment process

**Don't use when:**
- ❌ You just pushed code (Vercel auto-deploys on push if connected to Git)
- ❌ You want to test locally first (use `vercel` CLI instead)

---

## Troubleshooting

### "Secret not found" Error

**Problem:** Workflow fails with "Secret RENDER_DEPLOY_HOOK_BACKEND is not set"

**Solution:**
1. Verify secret exists in GitHub repo settings
2. Check secret name is **exactly** `RENDER_DEPLOY_HOOK_BACKEND` (case-sensitive)
3. Ensure secret is set for Actions (not Dependabot)

### "HTTP 401 Unauthorized" Error

**Problem:** Deploy hook returns 401

**Solution:**
1. Regenerate deploy hook in Render/Vercel dashboard
2. Update secret in GitHub with new URL
3. Ensure URL includes authentication token

### "HTTP 404 Not Found" Error

**Problem:** Deploy hook returns 404

**Solution:**
1. Verify service still exists in Render/Vercel
2. Check deploy hook URL is complete (not truncated)
3. Regenerate deploy hook if service was recreated

### Workflow Doesn't Appear in Actions Tab

**Problem:** Manual Deploy workflow not visible

**Solution:**
1. Ensure `manual_deploy.yml` is pushed to `main` branch
2. GitHub parses workflows from default branch only
3. Check `.github/workflows/` directory structure is correct

---

## Related Documentation

- [Deployment Guide](../../docs/developer_guides/05_DEPLOYMENT_GUIDE.md)
- [Environment Configuration](../../docs/knowledge_base/technical_references/environment_configuration.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

*Last Updated: 2025-10-26*
