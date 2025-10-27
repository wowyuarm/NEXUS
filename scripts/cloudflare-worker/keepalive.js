/**
 * Cloudflare Workers Cron - Backend Keepalive
 * 
 * Pings NEXUS backend every 10 minutes to prevent Render cold starts.
 * More reliable than GitHub Actions scheduled workflows.
 * 
 * Setup:
 * 1. Create Cloudflare account (free)
 * 2. Install Wrangler CLI: npm install -g wrangler
 * 3. Login: wrangler login
 * 4. Update backend URL in wrangler.toml
 * 5. Deploy: wrangler deploy
 * 
 * Free tier limits:
 * - 100,000 requests/day (we need ~144)
 * - 10ms CPU time per request
 * - No egress fees
 */

export default {
  async scheduled(event, env, ctx) {
    // Backend health endpoint
    const BACKEND_URL = env.BACKEND_URL || 'https://nexus-backend-tp8m.onrender.com/api/v1/health';
    
    console.log(`[${new Date().toISOString()}] Pinging backend: ${BACKEND_URL}`);
    
    try {
      const startTime = Date.now();
      
      // Ping backend with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout
      
      const response = await fetch(BACKEND_URL, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'User-Agent': 'Cloudflare-Workers-Keepalive/1.0',
          'X-Keepalive': 'true'
        }
      });
      
      clearTimeout(timeoutId);
      
      const duration = Date.now() - startTime;
      const status = response.status;
      
      if (status === 200) {
        console.log(`✅ Backend responded in ${duration}ms (status: ${status})`);
      } else {
        console.warn(`⚠️ Backend responded with status ${status} in ${duration}ms`);
      }
      
      // Log to analytics (optional)
      if (env.ANALYTICS_ENABLED === 'true') {
        await logAnalytics(env, {
          timestamp: new Date().toISOString(),
          status: status,
          duration: duration,
          success: status === 200
        });
      }
      
      return new Response(JSON.stringify({
        success: true,
        status: status,
        duration: duration,
        timestamp: new Date().toISOString()
      }), {
        headers: { 'Content-Type': 'application/json' }
      });
      
    } catch (error) {
      console.error(`❌ Failed to ping backend: ${error.message}`);
      
      // Log error to analytics (optional)
      if (env.ANALYTICS_ENABLED === 'true') {
        await logAnalytics(env, {
          timestamp: new Date().toISOString(),
          error: error.message,
          success: false
        });
      }
      
      return new Response(JSON.stringify({
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  },
  
  // Optional: HTTP endpoint for manual testing
  async fetch(request, env, ctx) {
    return new Response(JSON.stringify({
      message: 'Keepalive worker is running',
      nextScheduled: 'Every 10 minutes via Cron Trigger',
      backendUrl: env.BACKEND_URL || 'Not configured'
    }), {
      headers: { 'Content-Type': 'application/json' }
    });
  }
};

/**
 * Optional: Log analytics to Cloudflare Analytics Engine or KV
 */
async function logAnalytics(env, data) {
  try {
    // Option 1: Use Cloudflare Workers Analytics Engine (requires paid plan)
    // await env.ANALYTICS.writeDataPoint({
    //   blobs: [data.timestamp],
    //   doubles: [data.duration],
    //   indexes: [data.status]
    // });
    
    // Option 2: Use Cloudflare KV (free tier: 100,000 reads/day, 1,000 writes/day)
    if (env.KEEPALIVE_KV) {
      const key = `keepalive:${Date.now()}`;
      await env.KEEPALIVE_KV.put(key, JSON.stringify(data), {
        expirationTtl: 86400 // Expire after 24 hours
      });
    }
  } catch (error) {
    console.error('Failed to log analytics:', error);
  }
}
