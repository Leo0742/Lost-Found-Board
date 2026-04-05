import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    define: {
      __YANDEX_MAPS_API_KEY__: JSON.stringify(env.YANDEX_MAPS_API_KEY ?? ''),
      __YANDEX_MAPS_SUGGEST_API_KEY__: JSON.stringify(env.YANDEX_MAPS_SUGGEST_API_KEY ?? ''),
    },
  }
})
