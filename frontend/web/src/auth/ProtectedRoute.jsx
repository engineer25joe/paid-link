import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';
import { LoadingScreen } from '../components/LoadingScreen.jsx';
import { dashboardPath } from './navigation.js';
export function ProtectedRoute({ roles }) { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <LoadingScreen />; if (!user) return <Navigate to="/login" replace state={{ from: { pathname: location.pathname } }} />; if (!roles?.includes(user.role)) return <Navigate to={dashboardPath(user.role)} replace />; return <Outlet />; }
