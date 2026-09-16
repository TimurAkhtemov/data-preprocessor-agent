import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

// The backend is loopback-only; DI_API_URL lets a second stack (for example a
// browser-test run) proxy to a backend on another local port.
const api = process.env.DI_API_URL ?? 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: { port: 5173, strictPort: true, proxy: { '/api': api } },
  preview: { proxy: { '/api': api } },
  build: { chunkSizeWarningLimit: 1800 },
})
