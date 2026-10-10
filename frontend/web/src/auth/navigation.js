export const ROLES = ['learner', 'creator', 'admin'];
export const PUBLIC_PATHS = ['/', '/login', '/register', '/explore'];

export function dashboardPath(role) { return ROLES.includes(role) ? `/${role}` : '/'; }
export function canAccessPath(pathname, role) {
  if (PUBLIC_PATHS.includes(pathname)) return true;
  if (pathname === '/workspace') return ROLES.includes(role);
  return ROLES.some((candidate) => pathname === `/${candidate}` && candidate === role);
}
export function loginDestination(from, role) {
  const pathname = typeof from === 'string' ? from : from?.pathname;
  return pathname && canAccessPath(pathname, role) ? pathname : dashboardPath(role);
}
