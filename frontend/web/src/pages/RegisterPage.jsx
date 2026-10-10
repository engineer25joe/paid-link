import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext.jsx';
import { getApiErrorMessage } from '../api/errors.js';

// Registration uses the existing learner-only endpoint and enters the shared marketplace after success.
export function RegisterPage() {
  const { register } = useAuth();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    const details = Object.fromEntries(new FormData(event.currentTarget));
    try { await register(details); navigate('/', { replace: true }); }
    catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(false); }
  }
  return <section className="auth-page"><div className="auth-aside"><p className="eyebrow">Start learning</p><h1>Curiosity gets<br/>you places.</h1><p>Explore practical resources built to help you learn something that matters.</p></div><section className="form-card"><p className="eyebrow">Join the community</p><h2>Create your account</h2><p>New accounts begin with the learner role.</p><form onSubmit={submit}><label>Username<input name="username" autoComplete="username" required/></label><label>Email<input name="email" type="email" autoComplete="email" required/></label><label>Phone number<input name="phone_number" type="tel" autoComplete="tel" required/></label><label>Password<input name="password" type="password" autoComplete="new-password" minLength="8" required/></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button button-primary full" disabled={busy}>{busy ? 'Creating account…' : 'Create account'} <span aria-hidden="true">↗</span></button></form><div className="form-foot">Already have an account? <Link to="/login">Log in</Link></div></section></section>;
}
