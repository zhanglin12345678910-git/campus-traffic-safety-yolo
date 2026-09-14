import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const backendTarget = env.VITE_DEV_API_TARGET || 'http://127.0.0.1:8000'
  return {
    plugins: [
      vue(),
      Components({
        dts: false,
        resolvers: [ElementPlusResolver({ importStyle: false })],
      }),
    ],
    server: {
      port: 5173,
      proxy: {
        '/api': backendTarget,
        '/uploads': backendTarget,
        '/outputs': backendTarget,
      },
    },
  }
})
