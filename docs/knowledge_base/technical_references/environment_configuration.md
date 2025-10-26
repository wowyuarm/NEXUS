# Environment Configuration

## Overview

This document provides a comprehensive reference for configuring the NEXUS project across different environments (local development vs. production deployment on Vercel + Render).

**Current Deployment Architecture:**
- **Frontend (AURA)**: Deployed on Vercel as static site (global CDN)
- **Backend (NEXUS)**: Deployed on Render as Docker container (Singapore region)
- **Communication**: Direct HTTPS/WSS connections from browser to backend

---

## Table of Contents

1. [Architecture Context](#architecture-context)
2. [Frontend Configuration](#frontend-configuration)
3. [Backend Configuration](#backend-configuration)
4. [Environment Variable Flow](#environment-variable-flow)
5. [Network Communication](#network-communication)
6. [Configuration Files Reference](#configuration-files-reference)
7. [Common Issues](#common-issues)
8. [Best Practices](#best-practices)

---

## Architecture Context

### System Components

| Component | Technology | Deployment | Purpose |
|-----------|-----------|------------|---------|
| **AURA (Frontend)** | React 19 + Vite + TypeScript | Vercel (CDN) | User interface, static assets |
| **NEXUS (Backend)** | Python 3.11 + FastAPI | Render (Docker) | API, WebSocket, LLM orchestration |
| **MongoDB Atlas** | MongoDB 7.0 | Cloud | Persistent data storage |
| **GitHub Actions** | Workflow automation | GitHub | Backend keepalive (prevents cold starts) |

### Communication Architecture

#### Development Environment
```
┌─────────────┐     Vite Dev Proxy     ┌──────────────┐
│   Browser   │ ──────────────────────> │   Backend    │
│ localhost   │                         │ localhost    │
│   :5173     │ <────────────────────── │    :8000     │
└─────────────┘                         └──────────────┘
```

**Key Points:**
- Frontend runs on Vite dev server with hot reload
- Vite proxy forwards `/api/*` and `/ws/*` to backend
- Single `.env` file configures both services
- CORS not needed (same-origin via proxy)

#### Production Environment
```
┌─────────────┐                         ┌──────────────┐
│   Browser   │ ──── HTTPS/WSS ───────> │   Backend    │
│  (Global)   │                         │  (Render)    │
└─────────────┘                         │  Singapore   │
       │                                └──────────────┘
       │ HTTPS (static)                        │
       ↓                                       │
┌─────────────┐                               │
│   Vercel    │                               │
│   CDN Edge  │                               │
└─────────────┘                               │
       ↑                                       ↓
       │                                ┌──────────────┐
       │                                │   MongoDB    │
       └──────── Build-time ───────────│   Atlas      │
         Environment Variables         └──────────────┘
```

**Key Points:**
- Frontend served from Vercel's global edge network (<2s load time)
- Backend on Render (Singapore for low latency to China)
- **Direct connections** - Browser connects to backend URL directly
- **CORS configured** - Backend allows Vercel domain origins
- **Build-time env vars** - Backend URLs baked into static bundle
- **GitHub Actions** - Pings backend every 10 minutes to prevent sleep

---

## Frontend Configuration

### Development Environment (.env)

**Location:** `/NEXUS/.env` (project root, gitignored)

```bash
# Backend Connection (Local Development)
VITE_NEXUS_BASE_URL=http://localhost:8000

# Optional: Environment identifier
VITE_AURA_ENV=development

# Optional: Application name
VITE_APP_NAME=AURA
```

**How It Works:**
1. **Vite loads** `.env` from parent directory (`envDir: '..'` in vite.config.ts)
2. **Dev server proxy** configured with `VITE_NEXUS_BASE_URL`:
   ```typescript
   // vite.config.ts
   proxy: {
     '/api': { target: env.VITE_NEXUS_BASE_URL || 'http://localhost:8000' },
     '/ws': { target: env.VITE_NEXUS_BASE_URL || 'http://localhost:8000', ws: true }
   }
   ```
3. **Frontend code** reads via `import.meta.env.VITE_NEXUS_BASE_URL`
4. **URL construction** in `config/nexus.ts`:
   ```typescript
   const devBase = import.meta.env.VITE_NEXUS_BASE_URL || 'http://localhost:8000';
   wsUrl = `${devBase.replace('http', 'ws')}/api/v1/ws`;
   apiUrl = `${devBase}/api/v1`;
   ```

**Key Files:**
- `aura/vite.config.ts` - Loads env and configures proxy
- `aura/src/config/nexus.ts` - Centralized configuration logic
- `aura/src/services/websocket/manager.ts` - Uses `getNexusConfig()`
- `aura/src/features/command/api.ts` - Uses `getNexusConfig()`

### Production Environment (Vercel)

**Configuration Location:** Vercel Dashboard > Project > Settings > Environment Variables

**Required Variables:**

| Variable | Example Value | Environment | Purpose |
|----------|--------------|-------------|---------|
| `VITE_AURA_WS_URL` | `wss://nexus-backend-xxx.onrender.com/api/v1/ws` | Production, Preview | WebSocket endpoint |
| `VITE_AURA_API_URL` | `https://nexus-backend-xxx.onrender.com/api/v1` | Production, Preview | REST API endpoint |
| `VITE_AURA_ENV` | `production` | Production | Environment identifier (optional) |
| `VITE_APP_NAME` | `AURA` | Production, Preview | Application name (optional) |

**Important Notes:**
- ⚠️ **Build-time variables** - These are baked into the static bundle during build
- Changes require **redeployment** to take effect (`vercel --prod`)
- Use **wss://** (not https://) for WebSocket URL
- Get backend URL from Render Dashboard after deployment

**Build Process:**
```
1. Vercel triggers build on git push
   ↓
2. Reads environment variables from dashboard
   ↓
3. Runs: cd aura && npm install && npm run build
   ↓
4. Vite replaces import.meta.env.VITE_* during build
   ↓
5. Static bundle contains hardcoded backend URLs
   ↓
6. Deploys to global CDN
```

**Runtime Logic** (`aura/src/config/nexus.ts`):
```typescript
export const getNexusConfig = (): NexusConfig => {
  const env = import.meta.env.PROD ? 'production' : 'development';
  
  let wsUrl = import.meta.env.VITE_AURA_WS_URL;
  let apiUrl = import.meta.env.VITE_AURA_API_URL;
  
  if (env === 'production') {
    if (!wsUrl || !apiUrl) {
      console.error('❌ Missing backend URLs in production!');
      // Fallback URLs (will fail but provide clear error)
      wsUrl = 'wss://backend-not-configured/api/v1/ws';
      apiUrl = 'https://backend-not-configured/api/v1';
    }
  } else {
    // Development: Use localhost or explicit override
    const devBase = import.meta.env.VITE_NEXUS_BASE_URL || 'http://localhost:8000';
    wsUrl = wsUrl || `${devBase.replace('http', 'ws')}/api/v1/ws`;
    apiUrl = apiUrl || `${devBase}/api/v1`;
  }
  
  return { env, wsUrl, apiUrl };
};
```

**Verification:**
Open browser console after deployment:
```javascript
// Should see your actual backend URLs
🔗 Connecting to WebSocket: wss://nexus-backend-xxx.onrender.com/api/v1/ws
```

### Centralized Configuration Pattern

All frontend code gets backend URLs through **one function**:

```typescript
// ✅ CORRECT - Use centralized config
import { getNexusConfig } from '@/config/nexus';

const config = getNexusConfig();
const wsUrl = config.wsUrl;
const apiUrl = config.apiUrl;

// ❌ WRONG - Don't read env vars directly
const wsUrl = import.meta.env.VITE_AURA_WS_URL;  // Don't do this!
```

**Files Using This Pattern:**
- `aura/src/services/websocket/manager.ts`
- `aura/src/features/command/api.ts`
- `aura/src/features/command/commandExecutor.ts`

---

## Backend Configuration

### Development Environment (.env)

**Location:** `/NEXUS/.env` (project root, gitignored)

```bash
# Environment
NEXUS_ENV=development

# LLM Provider API Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Database
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/nexus?retryWrites=true&w=majority

# Search Provider
TAVILY_API_KEY=your_tavily_api_key_here

# CORS (allow local frontend)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Logging
LOG_LEVEL=INFO
```

**How It Works:**
1. Python loads `.env` via `python-dotenv` or `os.getenv()`
2. Backend validates required environment variables on startup
3. CORS middleware allows origins in `ALLOWED_ORIGINS`
4. MongoDB connection established with `MONGO_URI`

### Production Environment (Render)

**Configuration Location:** `render.yaml` + Render Dashboard

**render.yaml Configuration:**
```yaml
services:
  - name: nexus-backend
    type: web
    env: docker
    repo: https://github.com/wowyuarm/NEXUS
    dockerfilePath: ./nexus/Dockerfile
    plan: free
    region: singapore  # Close to China for low latency
    
    envVars:
      # Python configuration
      - key: PYTHON_VERSION
        value: "3.11"
      - key: PYTHONPATH
        value: "/app"
      - key: PYTHONUNBUFFERED
        value: "1"
      
      # Secrets (set in Render Dashboard)
      - key: GEMINI_API_KEY
        sync: false  # Not in YAML, set manually in dashboard
      - key: OPENROUTER_API_KEY
        sync: false
      - key: DEEPSEEK_API_KEY
        sync: false
      - key: MONGO_URI
        sync: false
      - key: TAVILY_API_KEY
        sync: false
      
      # CORS (add Vercel domain after deployment)
      - key: ALLOWED_ORIGINS
        value: "http://localhost:5173,http://127.0.0.1:5173"
        # After Vercel deployment, add: https://your-app.vercel.app
      
      # Service configuration
      - key: NEXUS_ENV
        value: "production"
      - key: LOG_LEVEL
        value: "INFO"
```

**Security Best Practices:**
- ✅ `sync: false` means the value must be set in Render Dashboard (not committed to Git)
- ✅ API keys are encrypted in Render's secure storage
- ✅ Secrets are injected as environment variables at runtime
- ✅ Never commit API keys or passwords to Git

**Setting Secrets in Render:**
1. Go to Render Dashboard > `nexus-backend` service
2. Environment tab
3. Add Secret Environment Variables:
   - `GEMINI_API_KEY`
   - `OPENROUTER_API_KEY`
   - `DEEPSEEK_API_KEY`
   - `MONGO_URI`
   - `TAVILY_API_KEY`

**After Vercel Deployment:**
Update `ALLOWED_ORIGINS` in Render Dashboard to include your Vercel domain:
```
http://localhost:5173,http://127.0.0.1:5173,https://your-app.vercel.app
```

---

## Environment Variable Flow

### Development Flow

```
┌─────────────────────────────────────────────────────────┐
│ Developer creates .env file in project root             │
└─────────────────────────────────────────────────────────┘
                        │
                        ├──────────────────┬───────────────┐
                        │                  │               │
                        ↓                  ↓               ↓
              ┌──────────────┐   ┌──────────────┐  ┌──────────────┐
              │   Backend    │   │   Frontend   │  │  Vite Dev    │
              │  (Python)    │   │  (Runtime)   │  │   Server     │
              └──────────────┘   └──────────────┘  └──────────────┘
                      │                  │               │
                      ↓                  ↓               ↓
            os.getenv('...')    import.meta.env    proxy config
                      │                  │               │
                      ↓                  ↓               ↓
              CORS, DB, LLM      getNexusConfig()    /api → :8000
                                                     /ws → :8000
```

### Production Build Flow

```
┌─────────────────────────────────────────────────────────┐
│ git push → GitHub → Vercel/Render                       │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ↓                               ↓
┌──────────────────┐          ┌──────────────────┐
│  Vercel Build    │          │  Render Build    │
│  (Frontend)      │          │  (Backend)       │
└──────────────────┘          └──────────────────┘
        │                               │
        ↓                               ↓
  Read dashboard               Read render.yaml
  environment vars             + dashboard secrets
        │                               │
        ↓                               ↓
  npm run build                 Docker build
  (Vite replaces                uvicorn start
   import.meta.env)                    │
        │                               ↓
        ↓                       Backend running
  Static bundle                 (accepts requests)
  (with baked URLs)
        │
        ↓
  Deploy to CDN
  (global edge)
```

### Production Runtime Flow

```
┌────────────────────────────────────────────────────────┐
│ User visits https://your-app.vercel.app                │
└────────────────────────────────────────────────────────┘
                        │
                        ↓
┌────────────────────────────────────────────────────────┐
│ Vercel CDN serves static files (index.html, JS, CSS)   │
└────────────────────────────────────────────────────────┘
                        │
                        ↓
┌────────────────────────────────────────────────────────┐
│ Browser executes JS bundle                             │
│ - Reads baked-in VITE_AURA_WS_URL                      │
│ - Reads baked-in VITE_AURA_API_URL                     │
│ - getNexusConfig() returns production URLs             │
└────────────────────────────────────────────────────────┘
                        │
                        ↓
┌────────────────────────────────────────────────────────┐
│ Browser makes requests to backend directly:            │
│ - HTTPS: https://nexus-backend-xxx.onrender.com/api/v1 │
│ - WSS: wss://nexus-backend-xxx.onrender.com/api/v1/ws  │
└────────────────────────────────────────────────────────┘
                        │
                        ↓
┌────────────────────────────────────────────────────────┐
│ Render backend processes requests                      │
│ - CORS check passes (Vercel domain allowed)            │
│ - WebSocket connection established                     │
│ - REST API responds with JSON                          │
└────────────────────────────────────────────────────────┘
```

---

## Network Communication

### WebSocket Connection

#### Development
```typescript
// Frontend derives URL
const config = getNexusConfig();
// config.wsUrl = "ws://localhost:8000/api/v1/ws"

// Browser establishes WebSocket
new WebSocket("ws://localhost:8000/api/v1/ws/0x...")
  ↓
// Backend accepts connection
// Heartbeat every 30 seconds
// Event streaming begins
```

#### Production
```typescript
// Frontend uses baked-in URL
const config = getNexusConfig();
// config.wsUrl = "wss://nexus-backend-xxx.onrender.com/api/v1/ws"

// Browser establishes WebSocket
new WebSocket("wss://nexus-backend-xxx.onrender.com/api/v1/ws/0x...")
  ↓
// Render backend accepts connection
// CORS check: Vercel domain allowed ✓
// WebSocket tunnel established
// Heartbeat every 30 seconds
// Event streaming begins
```

### REST API Requests

#### Development
```javascript
// Frontend makes request
fetch("http://localhost:8000/api/v1/commands")
  ↓
// Vite dev proxy intercepts
proxy: { '/api': { target: 'http://localhost:8000' } }
  ↓
// Backend receives and responds
// CORS: localhost:5173 allowed ✓
```

#### Production
```javascript
// Frontend makes request
fetch("https://nexus-backend-xxx.onrender.com/api/v1/commands")
  ↓
// Direct HTTPS request (no proxy)
// CORS: Vercel domain allowed ✓
  ↓
// Render backend receives and responds
```

### CORS Configuration

**Backend** (`nexus/main.py` or similar):
```python
from fastapi.middleware.cors import CORSMiddleware

allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
# Development: ["http://localhost:5173", "http://127.0.0.1:5173"]
# Production: [..., "https://your-app.vercel.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Why CORS is needed:**
- Frontend domain: `https://your-app.vercel.app`
- Backend domain: `https://nexus-backend-xxx.onrender.com`
- **Different origins** → CORS required

---

## Configuration Files Reference

### `vercel.json`
**Purpose:** Vercel deployment configuration

```json
{
  "version": 2,
  "buildCommand": "cd aura && npm install && npm run build",
  "outputDirectory": "aura/dist",
  "installCommand": "cd aura && npm install",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/(.*)",
      "headers": [
        { "key": "X-Content-Type-Options", "value": "nosniff" },
        { "key": "X-Frame-Options", "value": "DENY" }
      ]
    }
  ]
}
```

**Key Points:**
- `buildCommand` runs from project root, builds in `aura/`
- `outputDirectory` points to Vite build output
- `rewrites` enable SPA routing (all routes → index.html)
- Security headers added to all responses

### `render.yaml`
**Purpose:** Render backend deployment configuration

See [Backend Configuration](#production-environment-render) section above.

### `aura/vite.config.ts`
**Purpose:** Frontend build configuration

```typescript
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(process.cwd(), '..'), '');
  
  return {
    envDir: path.resolve(process.cwd(), '..'),  // Load from parent directory
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': { target: env.VITE_NEXUS_BASE_URL || 'http://localhost:8000' },
        '/ws': { target: env.VITE_NEXUS_BASE_URL || 'http://localhost:8000', ws: true }
      }
    }
  };
});
```

### `aura/src/config/nexus.ts`
**Purpose:** Centralized configuration logic

See [Centralized Configuration Pattern](#centralized-configuration-pattern) section above.

### `.env.example`
**Purpose:** Environment variable template

```bash
# Copy this file to .env and fill in your values

# Backend Connection (Local Development)
VITE_NEXUS_BASE_URL=http://localhost:8000

# LLM Provider API Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Database
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/nexus

# Search Provider
TAVILY_API_KEY=your_tavily_api_key_here

# CORS (Local Development)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Optional
LOG_LEVEL=INFO
NEXUS_ENV=development
```

---

## Common Issues

### Issue 1: Frontend Connects to Localhost in Production

**Symptoms:**
```
🔗 Derived WebSocket URL: ws://localhost:8000/api/v1/ws
Failed to load resource: net::ERR_CONNECTION_REFUSED
```

**Root Cause:**
Environment variables not set in Vercel Dashboard, or deployment happened before variables were added.

**Solution:**
1. Verify Vercel Dashboard > Settings > Environment Variables:
   - `VITE_AURA_WS_URL` = `wss://nexus-backend-xxx.onrender.com/api/v1/ws`
   - `VITE_AURA_API_URL` = `https://nexus-backend-xxx.onrender.com/api/v1`
2. Redeploy: `vercel --prod`
3. Check browser console for updated URLs

### Issue 2: CORS Errors in Production

**Symptoms:**
```
Access to fetch at 'https://nexus-backend-xxx.onrender.com/api/v1/...'
from origin 'https://your-app.vercel.app' has been blocked by CORS policy
```

**Root Cause:**
Backend `ALLOWED_ORIGINS` doesn't include Vercel domain.

**Solution:**
1. Get your Vercel domain from deployment logs
2. Update `ALLOWED_ORIGINS` in Render Dashboard:
   ```
   http://localhost:5173,http://127.0.0.1:5173,https://your-app.vercel.app
   ```
3. Backend will restart automatically with new env vars

### Issue 3: WebSocket Connection Timeout

**Symptoms:**
```
WebSocket connection to 'wss://...' failed: Error during WebSocket handshake
```

**Possible Causes:**
1. Backend is sleeping (Render free tier cold start)
2. Wrong backend URL in Vercel env vars
3. Backend service is down

**Debugging Steps:**
1. Check backend health: `curl https://nexus-backend-xxx.onrender.com/api/v1/health`
2. Verify Vercel env vars match Render backend URL
3. Check Render backend logs for errors
4. Wait for keepalive to wake backend (GitHub Actions runs every 10 minutes)

### Issue 4: Environment Variables Not Taking Effect

**Symptoms:**
Changed Vercel env vars but frontend still uses old values.

**Root Cause:**
Environment variables are baked into static bundle at build time.

**Solution:**
Always redeploy after changing environment variables:
```bash
vercel --prod
```

### Issue 5: Backend Keeps Sleeping

**Symptoms:**
First request after 15+ minutes is very slow (20-30 seconds).

**Expected Behavior:**
Render free tier sleeps after 15 minutes of inactivity. This is normal.

**Solution:**
1. Verify GitHub Actions keepalive workflow is running:
   - Go to GitHub repo > Actions tab
   - Check "Backend Keepalive" workflow
   - Should run every 10 minutes
2. If workflow is failing, check logs and fix issues
3. Consider upgrading to Render paid plan ($7/month) for always-on service

---

## Best Practices

### Development Best Practices

1. **Always use `.env` file**
   - Copy from `.env.example`
   - Never commit `.env` to Git (.gitignored)
   - Set `VITE_NEXUS_BASE_URL=http://localhost:8000`

2. **Run backend before frontend**
   ```bash
   # Terminal 1: Backend
   source .venv/bin/activate
   cd nexus
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   
   # Terminal 2: Frontend
   cd aura
   pnpm dev
   ```

3. **Use browser DevTools**
   - Network tab: Verify proxy is working
   - Console tab: Check WebSocket connection logs
   - Look for "Derived WebSocket URL" messages

4. **Don't hardcode URLs**
   - ❌ `const url = "http://localhost:8000/api/v1"`
   - ✅ `const url = getNexusConfig().apiUrl`

### Production Best Practices

1. **Set environment variables before first deployment**
   - Vercel Dashboard: `VITE_AURA_WS_URL`, `VITE_AURA_API_URL`
   - Render Dashboard: API keys, `MONGO_URI`, `ALLOWED_ORIGINS`

2. **Update CORS after frontend deployment**
   - Get Vercel domain from deployment logs
   - Add to Render `ALLOWED_ORIGINS` immediately

3. **Verify deployment**
   ```bash
   # Check frontend loads
   curl -I https://your-app.vercel.app
   
   # Check backend health
   curl https://nexus-backend-xxx.onrender.com/api/v1/health
   
   # Check browser console
   # Should see production backend URLs, not localhost
   ```

4. **Monitor with GitHub Actions**
   - Actions tab: Verify keepalive workflow runs successfully
   - If failures occur, investigate and fix immediately

5. **Use Vercel Preview Deployments**
   - Test changes on preview URL before production
   - Set environment variables for "Preview" environment too

### Security Best Practices

1. **Never commit secrets**
   - Use `.env` file locally (gitignored)
   - Use dashboard secrets in production
   - Mark `sync: false` in `render.yaml` for sensitive values

2. **Minimize CORS origins**
   - Only allow necessary domains
   - Remove old/unused domains regularly

3. **Use HTTPS/WSS in production**
   - Never use HTTP/WS for production
   - Vercel and Render provide free SSL certificates

4. **Rotate API keys periodically**
   - Update in Render Dashboard
   - Backend restarts automatically with new keys

### Adding New Environment Variables

**Frontend (Vite):**
1. Prefix with `VITE_` to expose to client
2. Add to `.env.example` with documentation
3. For production, add to Vercel Dashboard
4. Redeploy to apply changes
5. Update this document

**Backend:**
1. Add to `.env.example` with documentation
2. If sensitive, mark `sync: false` in `render.yaml`
3. Add to Render Dashboard secrets
4. Update this document
5. Add validation in backend startup code

---

## References

### Related Documentation
- Deployment Guide: `../../developer_guides/05_DEPLOYMENT_GUIDE.md`
- Setup Guide: `../../developer_guides/01_SETUP_AND_RUN.md`
- Vercel Migration Task: `../../tasks/25-1026_vercel-frontend-migration.md`
- Architecture Overview: `../02_NEXUS_ARCHITECTURE.md`

### External Resources
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)
- [Vercel Environment Variables](https://vercel.com/docs/projects/environment-variables)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)

### Key Files
- `vercel.json` - Vercel deployment configuration
- `render.yaml` - Render backend configuration
- `aura/vite.config.ts` - Frontend build and dev server
- `aura/src/config/nexus.ts` - Centralized configuration
- `.env.example` - Environment variable template
- `.github/workflows/keepalive.yml` - Backend keepalive workflow

---

### Deprecated Architecture

The old Render frontend architecture (with nginx reverse proxy) was deprecated on 2025-10-26. For reference, see:
- `docs/backup/old_render_frontend/README.md`
- `docs/backup/old_render_frontend/environment_configuration_old.md`

---

_Last Updated: 2025-10-26_  
_Maintainer: Update this document when environment configuration changes_
