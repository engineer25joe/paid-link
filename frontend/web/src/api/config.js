const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const rawBaseUrl = configuredBaseUrl || (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '');

if (!rawBaseUrl) {
  throw new Error('VITE_API_BASE_URL must be set for production builds.');
}

const parsedBaseUrl = new URL(rawBaseUrl);
if (!['http:', 'https:'].includes(parsedBaseUrl.protocol) || parsedBaseUrl.username || parsedBaseUrl.password || parsedBaseUrl.pathname !== '/' || parsedBaseUrl.search || parsedBaseUrl.hash) {
  throw new Error('VITE_API_BASE_URL must be an HTTP(S) API origin without credentials, path, query, or fragment.');
}
if (import.meta.env.PROD && (parsedBaseUrl.protocol !== 'https:' || ['localhost', '127.0.0.1', '::1'].includes(parsedBaseUrl.hostname))) {
  throw new Error('Production VITE_API_BASE_URL must use HTTPS and cannot point to localhost.');
}

export const API_BASE_URL = parsedBaseUrl.origin;
export const API_PATHS = {
  login: '/api/accounts/login/', register: '/api/accounts/register/', refresh: '/api/accounts/token/refresh/',
  profile: '/api/accounts/profile/', content: '/api/content/', myContent: '/api/content/my-content/',
  contentCreate: '/api/content/create/', creatorEarnings: '/api/accounts/creator/earnings/summary/',
  creatorContentEarnings: '/api/accounts/creator/earnings/content/', adminDashboard: '/api/admin/dashboard/',
  contentAccess: (id) => `/api/content/${id}/access/`, purchase: (id) => `/api/purchases/${id}/purchase/`,
  contentUpdate: (id) => `/api/content/${id}/update/`, contentPublish: (id) => `/api/content/${id}/publish/`,
};
