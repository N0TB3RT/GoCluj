import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const proxy = {
    '/api': {
      target: env.API_PROXY_TARGET || 'http://localhost:8000',
      changeOrigin: true,
    },
  }
  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: true,
      port: 3000,
      proxy,
      watch: { usePolling: true },
    },
    preview: { proxy },
  }
})
