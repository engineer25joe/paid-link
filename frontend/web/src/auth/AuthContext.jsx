import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, configureTokenProvider } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { viewModeFor, VIEW_MODES } from './navigation.js';
const AuthContext = createContext(null);
const KEY = 'paid-link-session';
const VIEW_KEY = 'paid-link-admin-view';
function readSession() { try { return JSON.parse(sessionStorage.getItem(KEY) || 'null'); } catch { return null; } }
function readAdminView() { const value = sessionStorage.getItem(VIEW_KEY); return VIEW_MODES.includes(value) ? value : 'admin'; }
export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession);
  const [adminView, setAdminView] = useState(readAdminView);
  const [loading, setLoading] = useState(Boolean(readSession()?.tokens?.access));
  const persist = useCallback((value) => { setSession(value); if (value) sessionStorage.setItem(KEY, JSON.stringify(value)); else sessionStorage.removeItem(KEY); }, []);
  const logout = useCallback(() => { sessionStorage.removeItem(VIEW_KEY); setAdminView('admin'); persist(null); }, [persist]);
  const refresh = useCallback(async () => { const current = readSession(); if (!current?.tokens?.refresh) return null; try { const result = await api.post(API_PATHS.refresh, { refresh: current.tokens.refresh }, { authenticated: false }); persist({ ...current, tokens: { ...current.tokens, ...result } }); return result.access; } catch { logout(); return null; } }, [persist, logout]);
  useEffect(() => { configureTokenProvider({ getAccess: () => readSession()?.tokens?.access, refresh, onExpired: logout }); }, [refresh, logout]);
  useEffect(() => { let active = true; if (!session?.tokens?.access) { setLoading(false); return () => { active = false; }; } api.get(API_PATHS.profile).then((user) => { if (active) persist({ ...readSession(), user }); }).catch(() => { if (active) logout(); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, []);
  const login = useCallback(async (credentials) => { const tokens = await api.post(API_PATHS.login, credentials, { authenticated: false }); const user = await api.get(API_PATHS.profile, { headers: { Authorization: `Bearer ${tokens.access}` } }); persist({ tokens, user }); return user; }, [persist]);
  const register = useCallback(async (details) => { const result = await api.post(API_PATHS.register, details, { authenticated: false }); const user = await api.get(API_PATHS.profile, { headers: { Authorization: `Bearer ${result.tokens.access}` } }); persist({ tokens: result.tokens, user }); return user; }, [persist]);
  const refreshProfile = useCallback(async () => { const user = await api.get(API_PATHS.profile); persist({ ...readSession(), user }); return user; }, [persist]);
  // Admin view selection only changes visible navigation; user.role stays authoritative.
  const setAdminViewMode = useCallback((mode) => {
    if (session?.user?.role !== 'admin' || !VIEW_MODES.includes(mode)) return;
    sessionStorage.setItem(VIEW_KEY, mode);
    setAdminView(mode);
  }, [session?.user?.role]);
  const viewMode = viewModeFor(session?.user?.role, adminView);
  const value = useMemo(() => ({ user: session?.user || null, loading, login, register, logout, refreshProfile, viewMode, setAdminViewMode }), [session, loading, login, register, logout, refreshProfile, viewMode, setAdminViewMode]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('useAuth must be used inside AuthProvider'); return value; }
