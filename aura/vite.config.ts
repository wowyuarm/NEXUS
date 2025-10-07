import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Load environment variables from parent directory's .env file
  // Only used in development mode for Vite dev server proxy
  const env = loadEnv(mode, path.resolve(process.cwd(), '..'), '');

  // Log loaded environment for debugging
  console.log('🏗️ Vite Configuration:');
  console.log('Mode:', mode);
  console.log('VITE_NEXUS_BASE_URL (dev proxy):', env.VITE_NEXUS_BASE_URL || 'http://localhost:8000');

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(process.cwd(), "./src"),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            // Separate React libraries into independent chunk
            'react-vendor': ['react', 'react-dom'],
            // Separate large UI library
            'framer-motion': ['framer-motion'],
            // Separate markdown-related libraries for lazy loading
            'markdown': ['react-markdown', 'remark-gfm', 'rehype-highlight'],
            // Separate code highlighting library
            'highlight': ['highlight.js'],
            // Separate ethers library
            'ethers': ['ethers'],
            // Separate state management library
            'zustand': ['zustand'],
          },
        },
      },
      // Set chunk size warning limit (optional)
      chunkSizeWarningLimit: 600,
    },
    server: {
      port: 5173, // Fixed port for consistency
      proxy: {
        // Development proxy: forward /api and /ws to backend
        // Production: nginx handles reverse proxy, no need for Vite proxy
        '/api': {
          target: env.VITE_NEXUS_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: env.VITE_NEXUS_BASE_URL?.replace('ws://', 'http://')?.replace('wss://', 'https://') || 'http://localhost:8000',
          ws: true,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
})
