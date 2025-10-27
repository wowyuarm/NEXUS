# Cloudflare Workers Keepalive

## Why Cloudflare Instead of GitHub Actions?

**GitHub Actions Problems:**
- ❌ Scheduled workflows are **not precise** (can delay 10-30 minutes)
- ❌ May skip runs during high load
- ❌ Lower priority for free tier accounts
- ❌ No guarantee of execution

**Cloudflare Workers Benefits:**
- ✅ **Precise cron** - Executes within seconds of scheduled time
- ✅ **Reliable** - 99.99% uptime SLA
- ✅ **Global distribution** - Runs from nearest edge location
- ✅ **Generous free tier** - 100,000 requests/day (we need 144)
- ✅ **Fast** - 10ms CPU time is more than enough for HTTP ping

---

## Setup Instructions (5 minutes)

### Prerequisites

- Cloudflare account (free): https://dash.cloudflare.com/sign-up
- Node.js installed (for Wrangler CLI)

### Step 1: Install Wrangler CLI

```bash
npm install -g wrangler
```

### Step 2: Login to Cloudflare

```bash
wrangler login
```

This will open a browser for authentication.

### Step 3: Update Backend URL

Edit `wrangler.toml` and replace the backend URL with your actual Render URL:

```toml
[env.production]
vars = { BACKEND_URL = "https://your-backend.onrender.com/api/v1/health" }
```

### Step 4: Deploy

```bash
cd scripts/cloudflare-worker
wrangler deploy
```

**Output:**
```
✨ Built successfully
✨ Uploaded successfully
✨ Published nexus-keepalive (1.23 sec)
   https://nexus-keepalive.your-subdomain.workers.dev
Cron Triggers:
  - */10 * * * *
```

### Step 5: Verify

1. **Check deployment:**
   ```bash
   curl https://nexus-keepalive.your-subdomain.workers.dev
   ```

2. **Monitor cron runs:**
   - Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
   - Workers & Pages > nexus-keepalive
   - Logs tab (real-time logs)
   - Metrics tab (request count, errors)

3. **Wait 10 minutes** and check logs for first cron run

---

## Configuration

### Cron Schedule

Edit `wrangler.toml` to change frequency:

```toml
[triggers]
# Every 10 minutes (default)
crons = ["*/10 * * * *"]

# Every 5 minutes (more aggressive)
# crons = ["*/5 * * * *"]

# Every 15 minutes (less frequent)
# crons = ["*/15 * * * *"]
```

**Cron syntax:**
```
*/10 * * * *
 │   │ │ │ │
 │   │ │ │ └─ Day of week (0-6, Sunday=0)
 │   │ │ └─── Month (1-12)
 │   │ └───── Day of month (1-31)
 │   └─────── Hour (0-23)
 └─────────── Minute (0-59)
```

### Environment Variables

Add more variables in `wrangler.toml`:

```toml
[env.production]
vars = { 
  BACKEND_URL = "https://...",
  ANALYTICS_ENABLED = "true",
  TIMEOUT_MS = "30000"
}
```

### Optional: Enable Analytics

Store keepalive metrics in Cloudflare KV:

1. **Create KV namespace:**
   ```bash
   wrangler kv:namespace create "KEEPALIVE_KV"
   ```

2. **Add to wrangler.toml:**
   ```toml
   [[kv_namespaces]]
   binding = "KEEPALIVE_KV"
   id = "your-kv-namespace-id"
   ```

3. **Uncomment analytics code** in `keepalive.js`

---

## Monitoring

### Real-time Logs

```bash
wrangler tail
```

Or view in dashboard: Workers & Pages > nexus-keepalive > Logs

**Example log output:**
```
2024-10-27T10:00:00.123Z [INFO] Pinging backend: https://nexus-backend-tp8m.onrender.com/api/v1/health
2024-10-27T10:00:00.456Z [INFO] ✅ Backend responded in 234ms (status: 200)
```

### Metrics

Dashboard > Workers & Pages > nexus-keepalive > Metrics

**Key metrics:**
- **Requests** - Should be 144/day (~6/hour)
- **Success rate** - Should be >99%
- **CPU time** - Should be <5ms per request
- **Errors** - Should be 0

---

## Troubleshooting

### "Cron not firing"

**Check:**
1. Deployment successful? `wrangler deployments list`
2. Cron triggers listed in deployment output?
3. Account verified? (Email verification required)

**Solution:** Redeploy with `wrangler deploy --force`

### "Backend not responding"

**Check:**
1. Backend URL correct in `wrangler.toml`?
2. Backend is actually running? (Check Render dashboard)
3. Timeout too short? (Increase in code)

**Debug:**
```bash
# Test manually
curl -v https://your-backend.onrender.com/api/v1/health
```

### "Too many requests"

**Free tier limits:**
- 100,000 requests/day
- 1,000 requests/minute

Our usage: **144 requests/day** (well within limits)

If exceeded, upgrade to Workers Paid ($5/month for 10 million requests)

---

## Cost Comparison

| Service | Free Tier | Our Usage | Cost |
|---------|-----------|-----------|------|
| **Cloudflare Workers** | 100,000 req/day | 144 req/day | $0 |
| GitHub Actions | 2,000 min/month | <20 min/month | $0 |
| UptimeRobot | 50 monitors | 1 monitor | $0 |
| Cron-job.org | 1 job | 1 job | $0 |

**Recommendation:** Cloudflare Workers (most reliable + free)

---

## Alternative: Render Cron Jobs

If you prefer staying within Render ecosystem:

**Pros:**
- ✅ Integrated with render.yaml
- ✅ No external service needed
- ✅ Free

**Cons:**
- ❌ Requires cron job service (separate from web service)
- ❌ Less precise than Cloudflare
- ❌ Uses your 750 free hours

**Setup:**

Add to `render.yaml`:

```yaml
services:
  - name: nexus-keepalive-cron
    type: cron
    schedule: "*/10 * * * *"
    dockerfilePath: ./scripts/render-cron/Dockerfile
    env: docker
```

---

## Disable GitHub Actions Keepalive

Once Cloudflare Workers is working, optionally disable GitHub Actions:

1. Go to `.github/workflows/keepalive.yml`
2. Add to top:
   ```yaml
   # Disabled: Using Cloudflare Workers instead (more reliable)
   # on:
   #   schedule:
   #     - cron: '*/10 * * * *'
   ```

Or delete the file entirely.

---

## References

- [Cloudflare Workers Docs](https://developers.cloudflare.com/workers/)
- [Cron Triggers Guide](https://developers.cloudflare.com/workers/configuration/cron-triggers/)
- [Wrangler CLI Docs](https://developers.cloudflare.com/workers/wrangler/)
- [Free Tier Limits](https://developers.cloudflare.com/workers/platform/limits/)

---

*Last Updated: 2025-10-27*
