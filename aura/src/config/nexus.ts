// Unified Configuration for NEXUS
// Reads from shared environment variables

export interface NexusConfig {
	env: 'development' | 'production';
	wsUrl: string;
	apiUrl: string;
}

// Read configuration from Vite environment variables
export const getNexusConfig = (): NexusConfig => {
	// Vite exposes only VITE_* and a few meta flags; rely on them
	const env: 'development' | 'production' = import.meta.env.PROD ? 'production' : 'development';
	
	// Read explicit backend URLs (required for Vercel deployment)
	let wsUrl = import.meta.env.VITE_AURA_WS_URL as string | undefined;
	let apiUrl = import.meta.env.VITE_AURA_API_URL as string | undefined;
	
	if (env === 'production') {
		// Production: Require explicit URLs (no reverse proxy)
		if (!wsUrl || !apiUrl) {
			console.error(
				'❌ PRODUCTION BUILD ERROR: Missing backend URLs!\n' +
				'Set in Vercel Dashboard > Settings > Environment Variables:\n' +
				'  VITE_AURA_WS_URL=wss://nexus-backend-xxx.onrender.com/api/v1/ws\n' +
				'  VITE_AURA_API_URL=https://nexus-backend-xxx.onrender.com/api/v1\n' +
				'\nGet backend URL from Render Dashboard after deployment.'
			);
			// Provide fallback to allow build to complete (will fail at runtime with clear error)
			wsUrl = wsUrl || 'wss://BACKEND_URL_NOT_CONFIGURED/api/v1/ws';
			apiUrl = apiUrl || 'https://BACKEND_URL_NOT_CONFIGURED/api/v1';
		}
	} else {
		// Development: Use localhost or explicit override
		const devBase = import.meta.env.VITE_NEXUS_BASE_URL as string | undefined || 'http://localhost:8000';
		wsUrl = wsUrl || `${devBase.replace('http', 'ws')}/api/v1/ws`;
		apiUrl = apiUrl || `${devBase}/api/v1`;
	}

	const config: NexusConfig = {
		env,
		wsUrl: wsUrl!,
		apiUrl: apiUrl!
	};

	// Runtime validation warning
	if (config.wsUrl.includes('NOT_CONFIGURED') || config.apiUrl.includes('NOT_CONFIGURED')) {
		console.warn('⚠️ Backend URLs not configured. WebSocket connection will fail.');
	}

	console.log('NEXUS Configuration:', config);
	return config;
};

export const nexusConfig = getNexusConfig();