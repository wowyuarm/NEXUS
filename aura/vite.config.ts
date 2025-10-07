import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig(({ mode }) => {
  // Load environment variables
  // In production (Render), env vars are provided directly
  // In development, load from parent directory's .env file
  let env;
  if (mode === 'production') {
    // Production: Use environment variables provided by Render
    env = {
      NEXUS_ENV: process.env.NEXUS_ENV || 'production',
      VITE_NEXUS_BASE_URL: process.env.VITE_NEXUS_BASE_URL || 'https://nexus-backend-tp8m.onrender.com'
    };
  } else {
    // Development: Load from parent directory's .env file
    env = loadEnv(mode, path.resolve(process.cwd(), '..'), '');
  }

  // Log loaded environment for debugging - Following the Single Gateway Principle
  console.log('🏗️ NEXUS Environment Configuration:');
  console.log('NEXUS_ENV:', env.NEXUS_ENV);
  console.log('VITE_NEXUS_BASE_URL:', env.VITE_NEXUS_BASE_URL);

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
        // Following the Single Gateway Principle - derive all URLs from VITE_NEXUS_BASE_URL
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
