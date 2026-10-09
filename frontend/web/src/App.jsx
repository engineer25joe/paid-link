import { Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './auth/ProtectedRoute.jsx';
import { useAuth } from './auth/AuthContext.jsx';
import { PlaceholderPage } from './components/PlaceholderPage.jsx';
import { AppLayout } from './layouts/AppLayout.jsx';
import { HomePage } from './pages/HomePage.jsx';
import { LoginPage } from './pages/LoginPage.jsx';
import { RegisterPage } from './pages/RegisterPage.jsx';
function IndexRedirect() { const { user } = useAuth(); return <Navigate to={user ? `/${user.role}` : '/'} replace />; }
export function App() { return <Routes><Route element={<AppLayout />}><Route index element={<HomePage />} /><Route path="login" element={<LoginPage />} /><Route path="register" element={<RegisterPage />} /><Route element={<ProtectedRoute roles={['learner']} />}><Route path="learner" element={<PlaceholderPage title="Your learning space" eyebrow="Learner" />} /></Route><Route element={<ProtectedRoute roles={['creator']} />}><Route path="creator" element={<PlaceholderPage title="Your creator space" eyebrow="Creator" />} /></Route><Route element={<ProtectedRoute roles={['admin']} />}><Route path="admin" element={<PlaceholderPage title="Platform overview" eyebrow="Admin" />} /></Route><Route path="workspace" element={<IndexRedirect />} /><Route path="*" element={<PlaceholderPage title="Page not found" eyebrow="404" description="The page you’re looking for doesn’t exist." />} /></Route></Routes>; }
