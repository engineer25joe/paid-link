// Keep URL recognition separate from navigation and API validation. Tokens are
// passed only to the backend and are never included in diagnostics.
export const WEB_ORIGIN = 'https://paidlinkweb.onrender.com';

export function parseGuestLink(rawUrl) {
  if (typeof rawUrl !== 'string' || rawUrl.trim() === '') return { type: 'none' };
  let url;
  try { url = new URL(rawUrl); } catch { return { type: 'unrelated' }; }
  const web = url.protocol === 'https:' && url.origin === WEB_ORIGIN;
  const appScheme = url.protocol === 'paidlink:' && ['shared', 'guest-access'].includes(url.hostname);
  const supported = web || appScheme;
  if (!supported) return { type: 'unrelated' };
  const match = web
    ? url.pathname.match(/^\/(shared|guest-access)(?:\/(.*))?\/?$/)
    : [null, url.hostname, url.pathname.replace(/^\//, '').replace(/\/$/, '')];
  if (!match || (web && !match[1])) return { type: 'unrelated' };
  const token = match[2];
  if (!token || token.length > 512 || /[/?#%\\]/.test(token)) return { type: 'malformed', kind: match[1] };
  return { type: match[1] === 'shared' ? 'share' : 'access', token };
}

// The public share endpoint is authoritative for share state. Its 200 response
// carries EXPIRED, REVOKED, or LIMIT REACHED without exposing protected content.
export function shareStateScreen(share) {
  if (share?.status === 'EXPIRED') return 'expired';
  if (share?.status === 'REVOKED') return 'revoked';
  if (share?.status === 'LIMIT REACHED') return 'limit';
  if (share?.status !== 'ACTIVE') return 'invalid';
  return 'active';
}

export function requestErrorScreen(error) {
  if (error?.status === 404) return 'invalid';
  if (error?.status === 410) return 'expired';
  if (error?.status >= 500 || !error?.status) return 'network';
  return 'error';
}

export function createGuestLinking(getInitialURL, subscribe) {
  const accept = (url) => {
    const parsed = parseGuestLink(url);
    return parsed.type === 'share' || parsed.type === 'access' || parsed.type === 'malformed' ? url : null;
  };
  return {
    prefixes: ['paidlink://', WEB_ORIGIN],
    config: { screens: { App: { screens: { SharedContent: 'shared/:token', GuestAccess: 'guest-access/:token', InvalidGuestLink: 'invalid-link' } } } },
    async getInitialURL() { return accept(await getInitialURL()); },
    subscribe(listener) { return subscribe((url) => { const accepted = accept(url); if (accepted) listener(accepted); }); },
    getStateFromPath(path, options) {
      const parsed = parseGuestLink(`${WEB_ORIGIN}/${path.replace(/^\//, '')}`);
      if (parsed.type === 'malformed') return { routes: [{ name: 'App', state: { routes: [{ name: 'InvalidGuestLink' }] } }] };
      return undefined;
    },
  };
}
