import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';

// Admin view controls are presentation preferences only; route/API permissions keep using user.role.
export function ProfileMenu() {
  const { user, viewMode, setAdminViewMode, logout } = useAuth();
  const navigate = useNavigate();
  async function signOut() { await logout(); navigate('/', { replace: true }); }
  function chooseView(mode) {
    setAdminViewMode(mode);
    navigate(mode === 'admin' ? '/admin' : mode === 'creator' ? '/creator/content' : '/', { replace: true });
  }
  return <details className="profile-menu"><summary><span className="avatar-mark">{user?.username?.slice(0, 1)?.toUpperCase() || 'U'}</span><span className="profile-name">{user?.username}</span><span className="menu-caret" aria-hidden="true">⌄</span></summary>
    <div className="profile-popover"><div className="profile-popover-heading"><strong>{user?.username}</strong><span>{user?.role}</span></div><Link to="/profile">Profile and settings</Link><Link to="/purchases">My purchases</Link>{(viewMode === 'creator' || user?.role === 'creator') && <><Link to="/creator/content">My content</Link><Link to="/creator/earnings">Earnings</Link></>}{user?.role === 'admin' && viewMode === 'admin' && <Link to="/admin">Admin workspace</Link>}
      {user?.role === 'admin' && <fieldset className="view-selector"><legend>Experience view</legend><p>Changes display only. Your administrator permissions remain active.</p>{[['learner', 'Learner View'], ['creator', 'Creator View'], ['admin', 'Admin View']].map(([mode, label]) => <button key={mode} className={viewMode === mode ? 'view-option is-selected' : 'view-option'} onClick={() => chooseView(mode)}>{label}<span>{viewMode === mode ? '✓' : ''}</span></button>)}</fieldset>}
      <button className="signout-option" onClick={signOut}>Sign out</button>
    </div>
  </details>;
}
