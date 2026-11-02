import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    // Forward /api calls to the local Functions host (api/ running on 7071)
    proxy: { '/api': 'http://localhost:7071' },
  },
})
