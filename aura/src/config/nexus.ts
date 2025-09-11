// Unified Configuration for NEXUS
// Reads from shared environment variables

export interface NexusConfig {
	env: 'development' | 'production';
	wsUrl: string;
	apiUrl: string;
}

// Default configuration
const defaultConfig: NexusConfig = {
	env: 'development',
	wsUrl: 'ws://localhost:8000/api/v1/ws',
	apiUrl: 'http://localhost:8000/api/v1'
};

// Read configuration from Vite environment variables
export const getNexusConfig = (): NexusConfig => {
	// Vite exposes only VITE_* and a few meta flags; rely on them
	const env: 'development' | 'production' = import.meta.env.PROD ? 'production' : 'development';
	
	// Prefer explicitly provided VITE_* variables if present
	let wsUrl = import.meta.env.VITE_AURA_WS_URL as string | undefined;
	let apiUrl = import.meta.env.VITE_AURA_API_URL as string | undefined;
	
	// For production, if not provided, use relative paths (served behind reverse proxy)
	if (env === 'production' && !wsUrl) {
		wsUrl = '/ws/api/v1/ws';
	}
	if (env === 'production' && !apiUrl) {
		apiUrl = '/api/v1';
	}
	
	// Fallback to development defaults if still not set
	wsUrl = wsUrl || defaultConfig.wsUrl;
	apiUrl = apiUrl || defaultConfig.apiUrl;

	const config: NexusConfig = {
		env,
		wsUrl,
		apiUrl
	};

	console.log('NEXUS Configuration:', config);
	return config;
};

export const nexusConfig = getNexusConfig();