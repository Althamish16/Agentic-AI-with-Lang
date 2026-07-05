import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Frontend dev server on :9000 (from .env frontend_port). All /api calls are
// proxied to the FastAPI backend on :5000 (from .env backend_port), so the
// browser sees a single origin and there are no CORS surprises in dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 9000,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
    },
  },
})
