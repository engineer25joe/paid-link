import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const configuredApiUrl = loadEnv(mode, process.cwd(), '').VITE_API_BASE_URL?.trim();

  if (mode === 'production') {
    if (!configuredApiUrl) {
      throw new Error('Set VITE_API_BASE_URL to the deployed API origin before building for production.');
    }

    const apiUrl = new URL(configuredApiUrl);
    const localHosts = ['localhost', '127.0.0.1', '::1'];
    if (
      apiUrl.protocol !== 'https:' ||
      apiUrl.username ||
      apiUrl.password ||
      apiUrl.pathname !== '/' ||
      apiUrl.search ||
      apiUrl.hash ||
      localHosts.includes(apiUrl.hostname)
    ) {
      throw new Error('Production VITE_API_BASE_URL must be a public HTTPS origin without credentials or a path.');
    }
  }

  return { plugins: [react()], server: { host: '0.0.0.0' } };
});
