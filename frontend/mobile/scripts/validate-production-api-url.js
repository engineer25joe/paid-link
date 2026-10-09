const productionBuild = process.env.EAS_BUILD_PROFILE === 'production';

if (!productionBuild) {
  process.exit(0);
}

const configuredUrl = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
if (!configuredUrl) {
  throw new Error('Set EXPO_PUBLIC_API_BASE_URL in the EAS production environment.');
}

const apiUrl = new URL(configuredUrl);
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
  throw new Error('Production EXPO_PUBLIC_API_BASE_URL must be a public HTTPS origin without credentials or a path.');
}
