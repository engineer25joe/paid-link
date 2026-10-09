import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext.jsx';
import { LoadingScreen } from '../components/LoadingScreen.jsx';
export function ProtectedRoute({ roles }) { const { user, loading } = useAuth(); const location = useLocation(); if (loading) return <LoadingScreen />; if (!user) return <Navigate to="/login" replace state={{ from: location }} />; if (roles?.length && !roles.includes(user.role)) return <Navigate to={`/${user.role}`} replace />; return <Outlet />; }
