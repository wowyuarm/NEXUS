# Environment Configuration

## Overview

This document provides a comprehensive reference for understanding and configuring the NEXUS project across different environments (local development vs. production deployment). It covers environment variables, build-time vs. runtime behavior, network architecture, and the critical decision points that enable the system to work correctly in both contexts.

**Key Architectural Principle**: NEXUS follows a **Single Gateway Architecture** where the frontend uses its own domain as the entry point, and nginx reverse proxy forwards requests to the backend. This eliminates CORS issues and provides a unified API surface.

---

## Architecture Context

### System Components
- **AURA (Frontend)**: React + TypeScript + Vite application
- **NEXUS (Backend)**: Python FastAPI service
- **Nginx**: Reverse proxy (production only)
- **Render**: Cloud deployment platform

### Communication Flows

#### Local Development
```
Browser (localhost:5173)
  ↓ (Vite dev server proxy)
Backend (localhost:8000)
```

#### Production (Render)
```
Browser (https://app.yxnexus.com)
  ↓ (Same-origin requests to /api and /ws)
Nginx (in AURA container)
  ↓ (Reverse proxy via BACKEND_ORIGIN)
Backend (https://nexus-backend-tp8m.onrender.com)
```

---

## Frontend Environment Configuration

### 1. Development Environment

**File**: `.env` (project root, gitignored)

```bash
# Backend connection for local development
VITE_NEXUS_BASE_URL=http://localhost:8000

# Optional overrides
VITE_AURA_ENV=development
VITE_APP_NAME=AURA
```

**How it works**:
1. Vite loads variables from `.env` at dev server startup
2. `vite.config.ts` reads `VITE_NEXUS_BASE_URL` and configures dev server proxy:
   - `/api/*` → `http://localhost:8000/api/*`
   - `/ws/*` → `ws://localhost:8000/ws/*`
3. Frontend code accesses via `import.meta.env.VITE_NEXUS_BASE_URL`
4. If variable is set, frontend uses it; otherwise falls back to `window.location.origin`

**Key Files**:
- `aura/vite.config.ts`: Loads env and configures dev proxy
- `aura/src/services/websocket/manager.ts`: WebSocket URL construction
- `aura/src/features/command/api.ts`: REST API base URL

### 2. Build Environment (Docker)

**File**: `aura/Dockerfile`

```dockerfile
# Builder stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN npm install -g pnpm@10
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm run build  # ← Build happens here
```

**Important**: 
- Environment variables from Render are **NOT** available during Docker build on Render's platform
- `VITE_NEXUS_BASE_URL` will be `undefined` in the built bundle
- This is **intentional** - frontend runtime code handles it gracefully

### 3. Runtime Environment (nginx container)

**File**: `aura/nginx.conf`

```nginx
location ^~ /api/v1/ws/ {
    proxy_pass ${BACKEND_ORIGIN};  # ← Injected at container startup
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    # ... other headers
}

location /api/ {
    proxy_pass ${BACKEND_ORIGIN};
    # ... proxy headers
}
```

**Container startup** (`aura/Dockerfile`):
```dockerfile
ENV BACKEND_ORIGIN=""
CMD sh -c "envsubst '\$BACKEND_ORIGIN' < /etc/nginx/conf.d/nginx.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"
```

**Render configuration** (`render.yaml`):
```yaml
envVars:
  - key: BACKEND_ORIGIN
    value: "https://nexus-backend-tp8m.onrender.com"
```

**Flow**:
1. Render injects `BACKEND_ORIGIN` as container env var
2. `envsubst` replaces `${BACKEND_ORIGIN}` in nginx config
3. Nginx starts with correct backend proxy target

### 4. Frontend Runtime Logic

**WebSocket URL Construction** (`aura/src/services/websocket/manager.ts`):
```typescript
private _getBaseUrl(): string {
  // Prefer configured base URL; fallback to current origin
  const configuredBase = (import.meta.env.VITE_NEXUS_BASE_URL || '').trim();
  const httpBase = configuredBase !== '' ? configuredBase : window.location.origin;

  // Convert HTTP to WebSocket protocol
  let wsUrl = httpBase.replace(/^http:/, 'ws:').replace(/^https:/, 'wss:');
  wsUrl = `${wsUrl}/api/v1/ws`;
  
  return wsUrl;
}
```

**REST API Base URL** (`aura/src/features/command/api.ts`):
```typescript
const configuredBase = (import.meta.env.VITE_NEXUS_BASE_URL || '').trim();
const httpBase = configuredBase !== '' ? configuredBase : window.location.origin;
const API_BASE_URL = `${httpBase}/api/v1`;
```

**Critical Decision Point**:
- **Local dev**: `VITE_NEXUS_BASE_URL` is set → frontend connects to `http://localhost:8000`
- **Production**: `VITE_NEXUS_BASE_URL` is empty → frontend uses `window.location.origin` → same-origin requests → nginx proxies to backend

---

## Backend Environment Configuration

### 1. Development Environment

**File**: `.env` (project root, gitignored)

```bash
# LLM Provider API Keys
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_key

# Database
MONGO_URI=mongodb://localhost:27017/nexus

# Search
TAVILY_API_KEY=your_tavily_key

# CORS (for local frontend)
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Optional
LOG_LEVEL=INFO
NEXUS_ENV=development
```

**How it works**:
1. Python loads `.env` via `python-dotenv` or similar
2. Backend reads vars via `os.getenv()`
3. CORS middleware allows `localhost:5173` for local dev

### 2. Production Environment (Render)

**File**: `render.yaml`

```yaml
services:
  - name: nexus-backend
    type: web
    env: docker
    envVars:
      # Secrets (set in Render dashboard)
      - key: GEMINI_API_KEY
        sync: false
      - key: OPENROUTER_API_KEY
        sync: false
      - key: MONGO_URI
        sync: false
      - key: TAVILY_API_KEY
        sync: false
      
      # Public config
      - key: ALLOWED_ORIGINS
        value: "https://aura-frontend-egej.onrender.com,https://app.yxnexus.com"
      - key: NEXUS_ENV
        value: "production"
      - key: LOG_LEVEL
        value: "INFO"
```

**Security Note**: `sync: false` means the value is **not** stored in `render.yaml` and must be set manually in Render dashboard under Environment → Secrets.

---

## Environment Variable Flow

### Local Development Flow

```
1. Developer creates .env file
   ↓
2. Backend: Python reads .env → os.getenv()
   Frontend: Vite loads .env → import.meta.env.VITE_*
   ↓
3. Vite dev server starts with proxy config
   ↓
4. Browser requests → Vite proxy → Backend
```

### Production Build Flow (Render)

```
1. Render receives git push
   ↓
2. Backend Docker build:
   - Copies code
   - Installs dependencies
   - Starts uvicorn with Render env vars
   ↓
3. Frontend Docker build:
   - Installs pnpm
   - Runs `pnpm install`
   - Runs `pnpm build` (VITE_NEXUS_BASE_URL unavailable)
   - Creates static bundle (window.location.origin fallback baked in)
   ↓
4. Frontend container startup:
   - envsubst injects BACKEND_ORIGIN into nginx.conf
   - nginx serves static files
   - nginx proxies /api and /ws to BACKEND_ORIGIN
```

### Runtime Flow (Production)

```
Browser navigates to https://app.yxnexus.com
   ↓
nginx serves index.html and static assets
   ↓
Frontend JS executes:
   - import.meta.env.VITE_NEXUS_BASE_URL is undefined
   - Falls back to window.location.origin (https://app.yxnexus.com)
   - Constructs API URL: https://app.yxnexus.com/api/v1
   - Constructs WS URL: wss://app.yxnexus.com/api/v1/ws
   ↓
Browser makes request to /api/v1/commands
   ↓
nginx matches location /api/ → proxy_pass to BACKEND_ORIGIN
   ↓
Backend (https://nexus-backend-tp8m.onrender.com) receives request
```

---

## Network Communication Architecture

### WebSocket Connection Lifecycle

#### Local Development
```
1. Frontend: const wsUrl = 'ws://localhost:8000/api/v1/ws'
2. Browser establishes WebSocket to ws://localhost:8000/api/v1/ws/{publicKey}
3. Backend accepts WebSocket connection
4. Heartbeat and event streaming begin
```

#### Production
```
1. Frontend: const wsUrl = 'wss://app.yxnexus.com/api/v1/ws'
   (window.location.origin = https://app.yxnexus.com)
2. Browser establishes WebSocket to wss://app.yxnexus.com/api/v1/ws/{publicKey}
3. nginx intercepts (matches location ^~ /api/v1/ws/)
4. nginx upgrades connection and proxies to wss://nexus-backend-tp8m.onrender.com/api/v1/ws/{publicKey}
5. Backend accepts proxied WebSocket
6. nginx maintains tunnel, forwarding frames bidirectionally
```

### REST API Requests

#### Local Development
```
fetch('http://localhost:8000/api/v1/commands')
  ↓ (Vite dev proxy)
Backend at http://localhost:8000
```

#### Production
```
fetch('https://app.yxnexus.com/api/v1/commands')
  ↓ (Same-origin, no CORS)
nginx location /api/ → proxy_pass
  ↓
Backend at https://nexus-backend-tp8m.onrender.com
```

---

## Configuration Files Reference

### `render.yaml`
**Purpose**: Defines both frontend and backend services for Render deployment

**Current Configuration**:
- Backend service: `nexus-backend`
  - Docker build from `nexus/Dockerfile`
  - Environment secrets for API keys
  - ALLOWED_ORIGINS set to frontend domains
  
- Frontend service: `aura-frontend`
  - Docker build from `aura/Dockerfile`
  - `BACKEND_ORIGIN` set to backend service URL
  - No `VITE_NEXUS_BASE_URL` (intentionally removed)

### `aura/vite.config.ts`
**Purpose**: Vite build configuration and dev server proxy

**Key Sections**:
```typescript
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(process.cwd(), '..'), '');
  
  return {
    // ... plugins, build config
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: env.VITE_NEXUS_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: env.VITE_NEXUS_BASE_URL || 'http://localhost:8000',
          ws: true,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
```

### `aura/nginx.conf`
**Purpose**: Production reverse proxy configuration

**Critical Locations**:
```nginx
# WebSocket endpoint
location ^~ /api/v1/ws/ {
    proxy_pass ${BACKEND_ORIGIN};
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $proxy_host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 86400;
    proxy_ssl_server_name on;
}

# REST API
location /api/ {
    proxy_pass ${BACKEND_ORIGIN};
    proxy_set_header Host $proxy_host;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_ssl_server_name on;
}
```

---

## Common Issues and Troubleshooting

### Issue 1: Frontend Connects to localhost in Production

**Symptoms**:
```
🔗 Derived WebSocket URL from NEXUS_BASE_URL: ws://localhost:8000/api/v1/ws
Failed to load resource: net::ERR_CONNECTION_REFUSED
```

**Root Cause**: 
- `import.meta.env.VITE_NEXUS_BASE_URL` has a hardcoded fallback to `localhost:8000`
- Environment variable not being injected during build

**Solution**:
Change fallback logic to use `window.location.origin`:
```typescript
const configuredBase = (import.meta.env.VITE_NEXUS_BASE_URL || '').trim();
const httpBase = configuredBase !== '' ? configuredBase : window.location.origin;
```

**Files to Update**:
- `aura/src/services/websocket/manager.ts`
- `aura/src/features/command/api.ts`
- `aura/src/features/command/commandExecutor.ts`

### Issue 2: CORS Errors in Production

**Symptoms**:
```
Access to fetch at 'https://nexus-backend.onrender.com/api/v1/...' from origin 'https://app.yxnexus.com' has been blocked by CORS policy
```

**Root Cause**: Frontend is directly calling backend URL instead of using same-origin requests

**Solution**:
1. Verify frontend uses `window.location.origin` (not direct backend URL)
2. Verify nginx reverse proxy is configured correctly
3. Check that `BACKEND_ORIGIN` env var is set in Render

### Issue 3: Environment Variables Not Available in Docker Build

**Symptoms**:
- Render env vars don't appear in built bundle
- `import.meta.env.VITE_*` is undefined in production

**Root Cause**: Render doesn't inject env vars into Docker build context

**Expected Behavior**: This is normal. Frontend should handle undefined gracefully by falling back to `window.location.origin`.

**Verification**:
Check browser console logs:
```
🔗 Derived WebSocket URL from NEXUS_BASE_URL: wss://app.yxnexus.com/api/v1/ws
```
If you see your frontend domain (not localhost), it's working correctly.

### Issue 4: WebSocket Connection Fails with 502 Bad Gateway

**Symptoms**:
```
WebSocket connection to 'wss://...' failed: Error during WebSocket handshake: Unexpected response code: 502
```

**Possible Causes**:
1. Backend service is down or restarting
2. nginx proxy configuration is incorrect
3. `BACKEND_ORIGIN` is pointing to wrong URL

**Debugging Steps**:
1. Check backend service health: `curl https://nexus-backend-tp8m.onrender.com/api/v1/health`
2. Verify nginx config was templated correctly (exec into container and check `/etc/nginx/conf.d/default.conf`)
3. Check Render logs for backend service
4. Verify `BACKEND_ORIGIN` env var in Render dashboard

---

## Best Practices

### For Local Development
1. Always create a `.env` file from `.env.example`
2. Set `VITE_NEXUS_BASE_URL=http://localhost:8000`
3. Run backend first, then frontend
4. Use browser DevTools Network tab to verify proxy is working

### For Production Deployment
1. **Never** hardcode backend URLs in frontend code
2. Use `window.location.origin` as fallback for all API/WS URLs
3. Set `BACKEND_ORIGIN` correctly in Render
4. Verify nginx template substitution in container startup logs
5. Test with browser console to see actual URLs being used

### For Adding New Environment Variables

**Frontend**:
1. Prefix with `VITE_` to make it available to frontend
2. Add to `.env.example` for documentation
3. Update this document with usage and purpose
4. Consider: is this needed at build time or runtime?
   - Build time: use `import.meta.env.VITE_*`
   - Runtime: use `window.location` or nginx env substitution

**Backend**:
1. Add to `.env.example`
2. If sensitive, mark as `sync: false` in `render.yaml`
3. Document in this file
4. Add validation in backend startup code

---

## References

### Related Documentation
- Architecture Overview: `../02_NEXUS_ARCHITECTURE.md`
- Setup Guide: `../../developer_guides/01_SETUP_AND_RUN.md`
- Render Deployment Log: `../../learn/2025-10-06-render-canonization-refactor.md`

### External Resources
- [Vite Environment Variables](https://vitejs.dev/guide/env-and-mode.html)
- [Nginx Reverse Proxy Config](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Render Environment Variables](https://render.com/docs/environment-variables)
- [Docker Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)

### Key Files
- `aura/vite.config.ts` - Frontend build and dev server config
- `aura/nginx.conf` - Production reverse proxy template
- `aura/Dockerfile` - Frontend container build
- `nexus/Dockerfile` - Backend container build
- `render.yaml` - Deployment configuration
- `.env.example` - Environment variable template

---

_Last Updated: 2025-10-07_  
_Maintainer: Update this document when environment configuration changes_

