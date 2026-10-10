import { useState } from 'react';
import { useAuth } from '../auth/AuthContext.jsx';
import { getApiErrorMessage } from '../api/errors.js';
import { PageIntro } from '../components/PageIntro.jsx';
import { APP_NAME } from '../config/brand.js';

// The current account API is read-only; this page does not imply profile edits are saved.
export function ProfilePage() {
  const { user, refreshProfile } = useAuth();
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  async function reload() {
    setError(''); setNotice('');
    try { await refreshProfile(); setNotice('Your profile was refreshed from the server.'); }
    catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
  }
  return <section className="page-shell"><PageIntro eyebrow="Your account" title="Profile and settings" description={`Account details and credit balance from the ${APP_NAME} API.`} action={<button className="button button-light" onClick={reload}>Refresh profile</button>}/>
    {error && <p className="notice notice-error" role="alert">{error}</p>}{notice && <p className="notice notice-success" role="status">{notice}</p>}
    <dl className="profile-grid"><div><dt>Username</dt><dd>{user?.username || '—'}</dd></div><div><dt>Email</dt><dd>{user?.email || '—'}</dd></div><div><dt>Phone number</dt><dd>{user?.phone_number || 'Not provided'}</dd></div><div><dt>Role</dt><dd>{user?.role || '—'}</dd></div><div><dt>Credit balance</dt><dd>{user?.credits ?? '—'} credits</dd></div><div><dt>Verification</dt><dd>{user?.is_verified ? 'Verified' : 'Not verified'}</dd></div></dl>
    <p className="fine-print">Profile editing and password changes are not available in the current account API.</p>
  </section>;
}
