import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig(({ mode }) => {
  // .env lives at the repo root, shared with the backend.
  const env = loadEnv(mode, path.resolve(process.cwd(), '..'), '')
  const apiTarget = env.VITE_API_BASE_URL || 'http://localhost:8000'

  return {
    plugins: [react()],
    envDir: path.resolve(process.cwd(), '..'),
    resolve: { alias: { '@': path.resolve(process.cwd(), 'src') } },
    server: {
      port: 5173,
      // Proxy in dev so the browser talks to one origin and no CORS or API
      // base-URL configuration is needed in the client.
      proxy: { '/api': { target: apiTarget, changeOrigin: true } },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
      rollupOptions: {
        output: {
          // Keep the two heavy visual libraries out of the entry chunk so the
          // landing page and the auth screens stay small.
          manualChunks: {
            react: ['react', 'react-dom', 'react-router-dom'],
            charts: ['recharts'],
            maps: ['leaflet', 'react-leaflet'],
          },
        },
      },
    },
  }
})
