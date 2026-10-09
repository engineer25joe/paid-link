import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import { api, configureTokenProvider } from '../api/client';
import { API_PATHS } from '../api/config';
const AuthContext = createContext(null);
const STORAGE_KEY = 'paid-link-session';
export function AuthProvider({ children }) {
  const [session, setSession] = useState(null); const [loading, setLoading] = useState(true);
  const persist = useCallback(async (value) => { setSession(value); if (value) await SecureStore.setItemAsync(STORAGE_KEY, JSON.stringify(value)); else await SecureStore.deleteItemAsync(STORAGE_KEY); }, []);
  const logout = useCallback(() => persist(null), [persist]);
  const refresh = useCallback(async () => { try { const value = await SecureStore.getItemAsync(STORAGE_KEY); const current = value ? JSON.parse(value) : null; if (!current?.tokens?.refresh) return null; const tokens = await api.post(API_PATHS.refresh, { refresh: current.tokens.refresh }, { authenticated: false }); await persist({ ...current, tokens: { ...current.tokens, ...tokens } }); return tokens.access; } catch { await logout(); return null; } }, [persist, logout]);
  useEffect(() => { configureTokenProvider({ getAccess: () => session?.tokens?.access, refresh, onExpired: logout }); }, [session, refresh, logout]);
  useEffect(() => { let active = true; SecureStore.getItemAsync(STORAGE_KEY).then(async (value) => { if (!value) return; const saved = JSON.parse(value); if (active) setSession(saved); const user = await api.get(API_PATHS.profile); if (active) await persist({ ...saved, user }); }).catch(() => { if (active) logout(); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, []);
  const login = useCallback(async (credentials) => { const tokens = await api.post(API_PATHS.login, credentials, { authenticated: false }); const user = await api.get(API_PATHS.profile, { headers: { Authorization: `Bearer ${tokens.access}` } }); await persist({ tokens, user }); return user; }, [persist]);
  const register = useCallback(async (details) => { const result = await api.post(API_PATHS.register, details, { authenticated: false }); const user = await api.get(API_PATHS.profile, { headers: { Authorization: `Bearer ${result.tokens.access}` } }); await persist({ tokens: result.tokens, user }); return user; }, [persist]);
  const value = useMemo(() => ({ user: session?.user || null, loading, login, register, logout }), [session, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error('useAuth must be used inside AuthProvider'); return value; }
