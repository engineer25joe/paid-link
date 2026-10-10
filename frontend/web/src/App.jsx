import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './auth/ProtectedRoute.jsx';
import { useAuth } from './auth/AuthContext.jsx';
import { dashboardPath } from './auth/navigation.js';
import { LoadingScreen } from './components/LoadingScreen.jsx';
import { PlaceholderPage } from './components/PlaceholderPage.jsx';
import { AppLayout } from './layouts/AppLayout.jsx';
import { ExplorePage } from './pages/ExplorePage.jsx';
import { HomePage } from './pages/HomePage.jsx';
import { LoginPage } from './pages/LoginPage.jsx';
import { RegisterPage } from './pages/RegisterPage.jsx';
import { WorkspacePage } from './pages/WorkspacePage.jsx';

function IndexRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  return <Navigate to={user ? dashboardPath(user.role) : '/'} replace />;
}

function AuthPageRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  return user ? <Navigate to={dashboardPath(user.role)} replace /> : <Outlet />;
}

export function App() {
  return <Routes><Route element={<AppLayout />}>
    <Route index element={<HomePage />} />
    <Route path="explore" element={<ExplorePage />} />
    <Route element={<AuthPageRedirect />}>
      <Route path="login" element={<LoginPage />} />
      <Route path="register" element={<RegisterPage />} />
    </Route>
    <Route element={<ProtectedRoute roles={['learner']} />}><Route path="learner" element={<Navigate to="/workspace" replace />} /></Route>
    <Route element={<ProtectedRoute roles={['creator']} />}><Route path="creator" element={<Navigate to="/workspace" replace />} /></Route>
    <Route element={<ProtectedRoute roles={['admin']} />}><Route path="admin" element={<Navigate to="/workspace" replace />} /></Route>
    <Route path="workspace" element={<ProtectedRoute roles={['learner', 'creator', 'admin']} />}><Route index element={<WorkspacePage />} /></Route>
    <Route path="*" element={<PlaceholderPage title="Page not found" eyebrow="404" description="The page you’re looking for doesn’t exist." />} />
  </Route></Routes>;
}
