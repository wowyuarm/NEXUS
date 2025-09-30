import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Load environment variables from root directory
export default defineConfig(({ mode }) => {
  // Load env file from the root directory (parent directory)
  const env = loadEnv(mode, path.resolve(process.cwd(), '..'), '');
  
  // Log loaded environment for debugging
  console.log('NEXUS Environment Configuration:');
  console.log('NEXUS_ENV:', env.NEXUS_ENV);
  console.log('NEXUS_WS_URL:', env.NEXUS_WS_URL);
  console.log('NEXUS_API_URL:', env.NEXUS_API_URL);

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
        '/api': {
          target: env.NEXUS_API_URL || 'http://localhost:8000',
          changeOrigin: true,
          secure: false,
        },
        '/ws': {
          target: env.NEXUS_WS_URL?.replace('ws://', 'http://') || 'http://localhost:8000',
          ws: true,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
})
