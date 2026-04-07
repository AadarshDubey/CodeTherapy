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
