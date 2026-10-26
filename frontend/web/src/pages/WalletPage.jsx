import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getCreditRate, getWallet, initiateTopup } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { PageIntro } from '../components/PageIntro.jsx';
import { estimateCredits } from '../hooks/useCountdown.js';
import { createIdempotencyKey } from '../api/idempotency.js';

export function WalletPage() {
  const { user, refreshProfile } = useAuth();
  const [wallet, setWallet] = useState({ transactions: [], payments: [] });
  const [rate, setRate] = useState('');
  const [amount, setAmount] = useState('');
  const [phone, setPhone] = useState(user?.phone_number || '');
  const [requestKey, setRequestKey] = useState('');
  const [state, setState] = useState({ loading: true, busy: false, error: '', notice: '' });

  async function loadWallet() {
    const result = await getWallet();
    setWallet(result);
    return result;
  }

  useEffect(() => {
    let active = true;
    Promise.all([getWallet(), getCreditRate()]).then(([current, conversion]) => {
      if (active) { setWallet(current); setRate(conversion.credit_to_kes_rate); setState((s) => ({ ...s, loading: false })); }
    }).catch((error) => { if (active) setState((s) => ({ ...s, loading: false, error: getApiErrorMessage(error.data, error.message) })); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const hasPending = wallet.payments.some((payment) => ['pending', 'outcome_unknown'].includes(payment.status));
    if (!hasPending) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const next = await loadWallet();
        const completed = next.payments.some((payment) => payment.status === 'completed' && wallet.payments.some((old) => old.id === payment.id && old.status !== 'completed'));
        if (completed) await refreshProfile();
      } catch { /* Preserve the last verified wallet state while polling. */ }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [wallet, refreshProfile]);

  async function topUp(event) {
    event.preventDefault(); setState((s) => ({ ...s, busy: true, error: '', notice: '' }));
    try {
      const key = requestKey || createIdempotencyKey();
      setRequestKey(key);
      const result = await initiateTopup(amount, phone, key);
      setState((s) => ({ ...s, notice: `M-Pesa request started for KES ${result.amount_kes}. At the displayed rate, ${result.credits_awarded} credits will be added only after provider verification.` }));
      await loadWallet();
      if (result.status === 'completed') await refreshProfile();
      if (result.status !== 'outcome_unknown') setRequestKey('');
    } catch (error) { setState((s) => ({ ...s, error: getApiErrorMessage(error.data, error.message) })); }
    finally { setState((s) => ({ ...s, busy: false })); }
  }

  const estimated = estimateCredits(amount, rate);
  return <section className="page-shell narrow-shell">
    <PageIntro eyebrow="Credits" title="Your wallet" description="View your verified balance and wallet history."/>
    <div className="wallet-summary"><span>Credit balance</span><strong>{user?.credits ?? '—'} credits</strong><Link className="button button-primary" to="#top-up">Top Up Credits</Link></div>
    <form id="top-up" className="editor-form" onSubmit={topUp}><h2>Top up with M-Pesa</h2><p>Conversion rate: <strong>1 credit = KES {rate || '…'}</strong>. Credits are added only after M-Pesa verification.</p>
      <label>Amount in KES<input required type="number" min="1" max="250000" step="1" value={amount} onChange={(e) => { setAmount(e.target.value); setRequestKey(''); }}/></label>
      {estimated && <p>Estimated credit award: <strong>{estimated} credits</strong></p>}
      <label>M-Pesa phone number<input required type="tel" autoComplete="tel" value={phone} onChange={(e) => { setPhone(e.target.value); setRequestKey(''); }} placeholder="0712345678"/></label>
      {state.error && <p className="notice notice-error" role="alert">{state.error}</p>}{state.notice && <p className="notice" role="status">{state.notice}</p>}
      <button className="button button-primary" disabled={state.busy || !amount || !phone}>{state.busy ? 'Starting M-Pesa request…' : 'Pay with M-Pesa'}</button>
    </form>
    <h2 className="section-title">Wallet history</h2>
    {state.loading ? <p className="notice" role="status">Loading wallet…</p> : state.error && !wallet.transactions.length ? <p className="notice notice-error" role="alert">{state.error}</p> : null}
    <div className="table-wrap"><table><thead><tr><th>Type</th><th>Credits</th><th>Balance after</th><th>Reason / reference</th><th>Date</th></tr></thead><tbody>
      {wallet.transactions.map((row) => <tr key={row.id}><td>{row.type}</td><td>{row.amount}</td><td>{row.balance_after}</td><td>{row.reason || row.description || row.payment_reference || '—'}{row.administrator && <small> by {row.administrator}</small>}</td><td>{new Date(row.created_at).toLocaleString()}</td></tr>)}
      {wallet.payments.map((row) => <tr key={`payment-${row.id}`}><td>M-Pesa top-up · {row.status}</td><td>{row.credits_awarded ?? '—'}</td><td>—</td><td>KES {row.amount_kes ?? row.amount}{row.reference ? ` · ${row.reference}` : ''}</td><td>{new Date(row.created_at).toLocaleString()}</td></tr>)}
      {!state.loading && !wallet.transactions.length && !wallet.payments.length && <tr><td colSpan="5">No wallet activity yet.</td></tr>}
    </tbody></table></div>
  </section>;
}
