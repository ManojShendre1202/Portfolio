import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-only proxy — mirrors the routing nginx does in prod (nginx.docker.conf),
// so `npm run dev` alone gives a fully working app with hot reload.
// Has no effect on `vite build`; prod routing is still nginx's job.
const DJANGO = 'http://127.0.0.1:8030'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Bind IPv4 explicitly: on Windows Node resolves "localhost" to ::1 only,
    // and nginx.dev.conf's upstream is 127.0.0.1:5173 -> 502 without this.
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api':    DJANGO,
      '/admin':  DJANGO,
      '/static': DJANGO,
      // Chat WS must come before the generic /ws rule (same as nginx).
      '/ws/readar-chat': { target: 'ws://127.0.0.1:8041', ws: true },
      '/ws':             { target: 'ws://127.0.0.1:8040', ws: true },
    },
  },
})
