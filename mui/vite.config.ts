import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    resolve: {
    alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      port: 5173,
      watch: {
        usePolling: true
      },
      proxy: {
        '/api': {
          target: env.CNSS_BASE_URL,
          ws: true,
          changeOrigin: true,
        }
      }
    },
  }
})
