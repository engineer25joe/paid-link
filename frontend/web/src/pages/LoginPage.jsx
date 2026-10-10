import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { loginDestination } from '../auth/navigation.js';
import { getApiErrorMessage } from '../api/errors.js';

// Sign-in preserves a valid protected destination, then returns ordinary logins to the shared home.
export function LoginPage() {
  const { login } = useAuth();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.currentTarget);
    try { const user = await login({ username: form.get('username'), password: form.get('password') }); navigate(loginDestination(location.state?.from, user.role), { replace: true }); }
    catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(false); }
  }
  return <section className="auth-page"><div className="auth-aside"><p className="eyebrow">Welcome back</p><h1>Pick up where<br/>you left off.</h1><p>Your next useful idea is only a lesson away.</p></div><section className="form-card"><p className="eyebrow">Sign in</p><h2>Good to see you</h2><p>Use your username and password to continue.</p><form onSubmit={submit}><label>Username<input name="username" autoComplete="username" required/></label><label>Password<input name="password" type="password" autoComplete="current-password" required/></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button button-primary full" disabled={busy}>{busy ? 'Signing in…' : 'Log in'} <span aria-hidden="true">↗</span></button></form><div className="form-foot">New here? <Link to="/register">Create a learner account</Link></div></section></section>;
}
