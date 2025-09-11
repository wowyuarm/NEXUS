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
  const env = import.meta.env.NEXUS_ENV || 
              import.meta.env.AURA_ENV || 
              import.meta.env.VITE_AURA_ENV || 
              'development';
  
  // Use URLs from environment variables
  let wsUrl = import.meta.env.NEXUS_WS_URL || 
              import.meta.env.AURA_WS_URL || 
              import.meta.env.VITE_AURA_WS_URL;
  let apiUrl = import.meta.env.NEXUS_API_URL || 
               import.meta.env.AURA_API_URL || 
               import.meta.env.VITE_AURA_API_URL;
  
  // For production, use relative paths with reverse proxy
  if (env === 'production' && !wsUrl) {
    wsUrl = '/ws/api/v1/ws';
  }
  if (env === 'production' && !apiUrl) {
    apiUrl = '/api/v1';
  }
  
  // Fallback to defaults if still not set
  wsUrl = wsUrl || defaultConfig.wsUrl;
  apiUrl = apiUrl || defaultConfig.apiUrl;

  const config: NexusConfig = {
    env: env as 'development' | 'production',
    wsUrl,
    apiUrl
  };

  console.log('NEXUS Configuration:', config);
  return config;
};

export const nexusConfig = getNexusConfig();