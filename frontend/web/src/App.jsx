import { Navigate, Outlet, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth/AuthContext.jsx';
import { ProtectedRoute } from './auth/ProtectedRoute.jsx';
import { LoadingScreen } from './components/LoadingScreen.jsx';
import { PlaceholderPage } from './components/PlaceholderPage.jsx';
import { AppLayout } from './layouts/AppLayout.jsx';
import { AdminListPage } from './pages/AdminListPage.jsx';
import { AdminEditContentPage } from './pages/AdminEditContentPage.jsx';
import { AdminPage } from './pages/AdminPage.jsx';
import { ContentDetailPage } from './pages/ContentDetailPage.jsx';
import { CreateContentPage } from './pages/CreateContentPage.jsx';
import { CreatorContentPage } from './pages/CreatorContentPage.jsx';
import { CreatorEarningsPage } from './pages/CreatorEarningsPage.jsx';
import { EditContentPage } from './pages/EditContentPage.jsx';
import { ExplorePage } from './pages/ExplorePage.jsx';
import { HomePage } from './pages/HomePage.jsx';
import { LibraryPage } from './pages/LibraryPage.jsx';
import { LoginPage } from './pages/LoginPage.jsx';
import { ProfilePage } from './pages/ProfilePage.jsx';
import { PurchasesPage } from './pages/PurchasesPage.jsx';
import { RegisterPage } from './pages/RegisterPage.jsx';

// Routes live here; page components own presentation and page-specific requests.
function AuthPageRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen/>;
  return user ? <Navigate to="/" replace/> : <Outlet/>;
}

function HomeAlias() { return <Navigate to="/" replace/>; }

export function App() {
  return <Routes><Route element={<AppLayout/>}>
    <Route index element={<HomePage/>}/>
    <Route path="home" element={<HomeAlias/>}/>
    <Route path="explore" element={<ExplorePage/>}/>
    <Route path="content/:id" element={<ContentDetailPage/>}/>
    <Route element={<AuthPageRedirect/>}><Route path="login" element={<LoginPage/>}/><Route path="register" element={<RegisterPage/>}/></Route>
    <Route element={<ProtectedRoute roles={['learner', 'creator', 'admin']}/> }>
      <Route path="library" element={<LibraryPage/>}/><Route path="purchases" element={<PurchasesPage/>}/><Route path="profile" element={<ProfilePage/>}/><Route path="settings" element={<Navigate to="/profile" replace/>}/>
      <Route path="workspace" element={<HomeAlias/>}/>
    </Route>
    <Route element={<ProtectedRoute roles={['learner']}/> }><Route path="learner" element={<HomeAlias/>}/></Route>
    <Route element={<ProtectedRoute roles={['creator', 'admin']}/> }>
      <Route path="creator" element={<Navigate to="/creator/content" replace/>}/><Route path="creator/content" element={<CreatorContentPage/>}/><Route path="creator/content/new" element={<CreateContentPage/>}/><Route path="creator/content/:id/edit" element={<EditContentPage/>}/><Route path="creator/earnings" element={<CreatorEarningsPage/>}/>
    </Route>
    <Route element={<ProtectedRoute roles={['admin']}/> }><Route path="admin" element={<AdminPage/>}/><Route path="admin/content/:id/edit" element={<AdminEditContentPage/>}/><Route path="admin/:section" element={<AdminListPage/>}/></Route>
    <Route path="*" element={<PlaceholderPage title="We can’t find that page" eyebrow="404" description="The page may have moved, or the address may be incorrect."/>}/>
  </Route></Routes>;
}
