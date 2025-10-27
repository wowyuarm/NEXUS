# NEXUS Scripts

Utility scripts for development, deployment, and maintenance.

---

## Directory Structure

```
scripts/
├── cloudflare-worker/     # Cloudflare Workers keepalive cron (recommended)
├── shell/                 # Shell scripts for local development
├── database_manager.py    # MongoDB database management utilities
└── file_combiner.py       # File combination utility for documentation
```

---

## Cloudflare Worker Keepalive

**Purpose:** Keep Render backend warm with precise 10-minute cron

**Why use this instead of GitHub Actions?**
- ✅ **Precise timing** - GitHub Actions can delay 10-30 minutes
- ✅ **Reliable** - 99.99% uptime, no skipped runs
- ✅ **Free** - 100,000 requests/day (we need 144)

**Setup:**
```bash
cd scripts/cloudflare-worker
npm install -g wrangler
wrangler login
wrangler deploy
```

**Documentation:** `cloudflare-worker/README.md`

---

## Shell Scripts

**Location:** `scripts/shell/`

### `run.sh`

Starts both backend and frontend for local development:

```bash
./scripts/shell/run.sh
```

**What it does:**
1. Starts backend (FastAPI) on port 8000
2. Starts frontend (Vite) on port 5173
3. Runs in background with process IDs logged

---

## Database Manager

**File:** `database_manager.py`

**Purpose:** MongoDB database management utilities

**Usage:**
```bash
python scripts/database_manager.py --help
```

**Features:**
- Database backup and restore
- Collection management
- Data migration tools
- Schema validation

---

## File Combiner

**File:** `file_combiner.py`

**Purpose:** Combine multiple files into single document for LLM context

**Usage:**
```bash
python scripts/file_combiner.py --input docs/ --output combined.md
```

**Use cases:**
- Generate documentation bundles
- Prepare context for AI coding assistants
- Create comprehensive references

---

## Keepalive Comparison

| Solution | Precision | Free Tier | Reliability | Setup Time |
|----------|-----------|-----------|-------------|------------|
| **Cloudflare Workers** | ✅ Exact | 100k req/day | 99.99% | 5 min |
| GitHub Actions | ❌ ±10-30min | 2000 min/month | ~95% | 2 min |
| UptimeRobot | ✅ Exact | 50 monitors | 99% | 3 min |
| Render Cron | ⚠️ ±5min | 750 hours/month | 98% | 10 min |

**Recommendation:** Use Cloudflare Workers for production keepalive.

---

## Related Documentation

- [Deployment Guide](../docs/developer_guides/05_DEPLOYMENT_GUIDE.md)
- [GitHub Workflows](../.github/workflows/README.md)
- [Environment Configuration](../docs/knowledge_base/technical_references/environment_configuration.md)

---

*Last Updated: 2025-10-27*
