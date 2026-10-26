import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { getApiErrorMessage } from '../api/errors.js';
import { PageIntro } from '../components/PageIntro.jsx';
import { APP_NAME } from '../config/brand.js';
import { createIdempotencyKey } from '../api/idempotency.js';

// The current account API is read-only; this page does not imply profile edits are saved.
export function ProfilePage() {
  const { user, refreshProfile } = useAuth();
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [phone, setPhone] = useState(user?.phone_number || '');
  const [amount, setAmount] = useState('');
  const [wallet, setWallet] = useState({ transactions: [], payments: [] });
  const [busy, setBusy] = useState(false);
  const [requestKey, setRequestKey] = useState('');
  const [application, setApplication] = useState(null);
  const [motivation, setMotivation] = useState('');
  const loadWallet = useCallback(() => { api.get(API_PATHS.walletTransactions).then(setWallet).catch((failure) => setError(getApiErrorMessage(failure.data, failure.message))); }, []);
  useEffect(() => { loadWallet(); if (user?.role === 'learner') api.get(API_PATHS.creatorApplications).then((data) => setApplication(data.application)).catch(() => {}); }, [loadWallet, user?.role]);
  async function reload() {
    setError(''); setNotice('');
    try { await refreshProfile(); setNotice('Your profile was refreshed from the server.'); }
    catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
  }
  async function topUp(event) {
    event.preventDefault(); setError(''); setNotice(''); setBusy(true);
    try {
      const key = requestKey || createIdempotencyKey(); setRequestKey(key);
      const result = await api.post(API_PATHS.initiateTopup, { amount, phone_number: phone, idempotency_key: key });
      setNotice(result.status === 'completed' ? 'Payment confirmed. Your balance has been updated.' : `Top-up request status: ${result.status}. Credits are added only after provider confirmation.`);
      const history = await api.get(API_PATHS.walletTransactions); setWallet(history);
      if (result.status === 'completed') await refreshProfile();
      if (result.status !== 'outcome_unknown') setRequestKey('');
    } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(false); }
  }
  async function refreshWallet() { setError(''); try { const updated = await api.get(API_PATHS.walletTransactions); const hasNewlyCompleted = updated.payments?.some((payment) => payment.status === 'completed' && !wallet.payments?.some((old) => old.id === payment.id && old.status === 'completed')); setWallet(updated); if (hasNewlyCompleted) { await refreshProfile(); setNotice('Payment verified and your credit balance has been refreshed.'); } } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); } }
  async function applyToCreate(event) { event.preventDefault(); setBusy(true); setError(''); try { const result = await api.post(API_PATHS.creatorApplications, { motivation }); setApplication(result.application); setNotice('Creator application submitted for administrator review.'); } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); } finally { setBusy(false); } }
  return <section className="page-shell"><PageIntro eyebrow="Your account" title="Profile and settings" description={`Account details and credit balance from the ${APP_NAME} API.`} action={<button className="button button-light" onClick={reload}>Refresh profile</button>}/>
    {error && <p className="notice notice-error" role="alert">{error}</p>}{notice && <p className="notice notice-success" role="status">{notice}</p>}
    <dl className="profile-grid"><div><dt>Username</dt><dd>{user?.username || '—'}</dd></div><div><dt>Email</dt><dd>{user?.email || '—'}</dd></div><div><dt>Phone number</dt><dd>{user?.phone_number || 'Not provided'}</dd></div><div><dt>Role</dt><dd>{user?.role || '—'}</dd></div><div><dt>Credit balance</dt><dd>{user?.credits ?? '—'} credits</dd></div><div><dt>Verification</dt><dd>{user?.is_verified ? 'Verified' : 'Not verified'}</dd></div></dl>
    <form className="auth-form" onSubmit={topUp}><h2>Top up credits</h2><p>Pay through the configured M-Pesa service. Credits appear after the server verifies payment.</p><label>Amount in KES<input type="number" min="1" max="250000" step="1" required value={amount} onChange={(event) => { setAmount(event.target.value); setRequestKey(''); }}/></label><label>M-Pesa phone number<input type="tel" required value={phone} onChange={(event) => { setPhone(event.target.value); setRequestKey(''); }}/></label><button className="button button-primary" disabled={busy}>{busy ? 'Starting payment…' : 'Top Up Credits'}</button></form>
    {user?.role === 'learner' && <section className="auth-form"><h2>Become a creator</h2>{application ? <p>Your application status: <strong>{application.status}</strong></p> : <form onSubmit={applyToCreate}><label>Tell us about the learning resources you plan to create<textarea required maxLength={2000} value={motivation} onChange={(event) => setMotivation(event.target.value)}/></label><button className="button button-light" disabled={busy}>Apply to become a creator</button></form>}</section>}
    <h2 className="section-title">Wallet activity</h2><button className="button button-light" onClick={refreshWallet}>Refresh wallet status</button><div className="table-wrap"><table><thead><tr><th>Activity</th><th>Amount</th><th>Status / balance</th><th>Date</th></tr></thead><tbody>{wallet.payments?.map((item) => <tr key={`p-${item.id}`}><td>M-Pesa top-up {item.reference ? `(${item.reference})` : ''}</td><td>{item.amount}</td><td>{item.status}</td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}{wallet.transactions?.map((item) => <tr key={`t-${item.id}`}><td>{item.description || item.type}</td><td>{item.amount}</td><td>Balance {item.balance_after}</td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}</tbody></table>{!wallet.payments?.length && !wallet.transactions?.length && <p>No wallet activity yet.</p>}</div>
    <p className="fine-print">Profile editing and password changes are not available in the current account API. Payment initiation requires provider credentials and confirmation callback configuration.</p>
  </section>;
}
