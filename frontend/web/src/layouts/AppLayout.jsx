import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { Brand } from '../components/Brand.jsx';
import { ProfileMenu } from '../components/ProfileMenu.jsx';
import { APP_SLOGAN } from '../config/brand.js';

// Shared shell keeps balances, wallet entry, and role-appropriate navigation visible.
export function AppLayout() {
  const { user, viewMode } = useAuth();
  return <div className="app-shell">
    <header className="topbar"><NavLink className="brand-link" to="/" aria-label="Go to home"><Brand/></NavLink>
      <nav className="main-nav" aria-label="Main navigation"><NavLink to="/" end>Home</NavLink><NavLink to="/explore">Explore</NavLink>{user && <NavLink to="/library">My Library</NavLink>}
        {(viewMode === 'creator' || user?.role === 'creator') && <><NavLink to="/creator/content">My Content</NavLink><NavLink to="/creator/earnings">Earnings</NavLink><NavLink to="/creator/shares">Share Links</NavLink></>}
        {user?.role === 'admin' && viewMode === 'admin' && <NavLink to="/admin">Admin</NavLink>}
      </nav>
      <div className="topbar-account">{user ? <><span className="balance-pill">{user.credits ?? '—'} <small>credits</small></span><NavLink className="button button-light nav-cta" to="/wallet">Top Up Credits</NavLink><ProfileMenu/></> : <><NavLink className="login-link" to="/login">Log in</NavLink><NavLink className="button button-primary nav-cta" to="/register">Join free</NavLink></>}</div>
    </header>
    <main id="main-content"><Outlet/></main>
    <footer className="site-footer"><Brand compact/><span>{APP_SLOGAN}</span><NavLink to="/explore">Explore resources</NavLink></footer>
  </div>;
}
