import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Backend defaults to 8010 so it does not collide with other local apps on 8000.
const backendTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8010'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: false,
    proxy: {
      '/api': {
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
})
