export const ROLES = ['learner', 'creator', 'admin'];
export const PUBLIC_PATHS = ['/', '/login', '/register', '/explore'];
export const VIEW_MODES = ['learner', 'creator', 'admin'];
const ADMIN_PATHS = ['/admin', ...['users', 'creators', 'learners', 'content', 'purchases', 'ledger', 'withdrawals'].map((section) => `/admin/${section}`)];
const CREATOR_PATHS = ['/creator', '/creator/content', '/creator/content/new', '/creator/earnings'];

export function dashboardPath(role) { return ROLES.includes(role) ? `/${role}` : '/'; }
// Display modes do not change the role used by ProtectedRoute or the server.
export function viewModeFor(role, requested) { return role === 'admin' && VIEW_MODES.includes(requested) ? requested : (ROLES.includes(role) ? role : 'learner'); }
export function canAccessPath(pathname, role) {
  if (PUBLIC_PATHS.includes(pathname)) return true;
  if (pathname === '/workspace') return ROLES.includes(role);
  if (/^\/content\/\d+$/.test(pathname)) return true;
  if (['/library', '/purchases', '/profile', '/settings'].includes(pathname)) return ROLES.includes(role);
  if ((CREATOR_PATHS.includes(pathname) || /^\/creator\/content\/\d+\/edit$/.test(pathname)) && ['creator', 'admin'].includes(role)) return true;
  if (ADMIN_PATHS.includes(pathname) || /^\/admin\/content\/\d+\/edit$/.test(pathname)) return role === 'admin';
  return ROLES.some((candidate) => pathname === `/${candidate}` && candidate === role);
}
export function loginDestination(from, role) {
  const pathname = typeof from === 'string' ? from : from?.pathname;
  return pathname && !['/login', '/register'].includes(pathname) && canAccessPath(pathname, role) ? pathname : '/';
}
