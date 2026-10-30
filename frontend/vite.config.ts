import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// Porta do backend FastAPI em desenvolvimento. Padrão 8000 (ver README.md);
// ajustável via BACKEND_PORT quando essa porta já estiver em uso por outro
// processo na máquina.
const backendPort = process.env.BACKEND_PORT ?? '8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  },
  server: {
    proxy: {
      // Em dev, o frontend roda em porta separada (npm run dev) e a API
      // fica no backend FastAPI. Em produção, o FastAPI serve os dois
      // juntos a partir de frontend/dist (ver docs/ARQUITETURA.md).
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
})
