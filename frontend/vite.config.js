import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:7860',
        changeOrigin: true,
        // Required for SSE: prevent proxy from buffering the response
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              // Disable buffering for SSE streams
              proxyRes.headers['Cache-Control'] = 'no-cache';
              proxyRes.headers['Connection'] = 'keep-alive';
            }
          });
        },
      },
      '/reset': {
        target: 'http://localhost:7860',
        changeOrigin: true,
      },
      '/step': {
        target: 'http://localhost:7860',
        changeOrigin: true,
      },
      '/state': {
        target: 'http://localhost:7860',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:7860',
        changeOrigin: true,
      },
    },
  },
});
