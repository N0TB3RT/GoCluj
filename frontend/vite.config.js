import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // expune serverul in afara containerului (pe 0.0.0.0)
    port: 3000, // forteaza portul asteptat de docker-compose
    watch: {
      usePolling: true // esential pentru ca hot-reload-ul sa mearga in Docker pe Windows
    }
  }
})