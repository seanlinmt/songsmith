import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  build: {
    // FastAPI serves the built SPA from server/web (mounted last, /api wins).
    outDir: '../server/web',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8788',
      '/files': 'http://127.0.0.1:8788',
    },
  },
});
