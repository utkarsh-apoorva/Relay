import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  define: {
    // Expose backend URL to the app at build time (set VITE_API_URL in Railway frontend env)
    // Falls back to '' (same origin) if not set — works for local dev proxy
    '__API_BASE__': JSON.stringify(process.env.VITE_API_URL || ''),
  },
}))
