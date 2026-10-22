import { useState } from 'react';
import { api } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { getApiErrorMessage } from '../api/errors.js';
import { createIdempotencyKey } from '../api/idempotency.js';
import { PageIntro } from '../components/PageIntro.jsx';

function toCents(value) {
  const match = String(value ?? '').trim().match(/^(\d+)(?:\.(\d{1,2}))?$/);
  if (!match) return null;
  return BigInt(match[1]) * 100n + BigInt((match[2] || '').padEnd(2, '0'));
}

function fromCents(cents) {
  const whole = cents / 100n;
  const fraction = String(cents % 100n).padStart(2, '0');
  return `${whole}.${fraction}`;
}

function errorMessage(error) {
  if (error?.status >= 500) return 'Unable to adjust credits. Please try again.';
  if (error instanceof TypeError) return 'Could not reach the server. Check your connection and try again.';
  return getApiErrorMessage(error?.data, error?.message || 'The adjustment could not be completed.');
}

export function AdminWalletPage() {
  const [query, setQuery] = useState('');
  const [users, setUsers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [direction, setDirection] = useState('add');
  const [amount, setAmount] = useState('');
  const [reason, setReason] = useState('');
  const [idempotencyKey, setIdempotencyKey] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [state, setState] = useState({ busy: false, error: '', result: '' });

  const amountCents = toCents(amount);
  const balanceCents = selected ? toCents(selected.credits) : null;
  const nextBalance = amountCents !== null && balanceCents !== null
    ? balanceCents + (direction === 'add' ? amountCents : -amountCents)
    : null;
  const validAdjustment = amountCents !== null && amountCents > 0n
    && nextBalance !== null && nextBalance >= 0n && Boolean(reason.trim());

  async function search(event) {
    event.preventDefault();
    setSelected(null);
    setConfirming(false);
    setState({ busy: false, error: '', result: '' });
    try {
      const data = await api.get(`${API_PATHS.adminWalletUsers}?search=${encodeURIComponent(query)}`);
      setUsers(data.results || []);
    } catch (error) {
      setState({ busy: false, error: errorMessage(error), result: '' });
    }
  }

  async function adjust() {
    if (!selected || !validAdjustment) return;
    setState((current) => ({ ...current, busy: true, error: '', result: '' }));
    try {
      const key = idempotencyKey || createIdempotencyKey();
      setIdempotencyKey(key);
      const result = await api.post(API_PATHS.adminWalletAdjustment(selected.id), {
        direction,
        amount,
        reason: reason.trim(),
        idempotency_key: key,
      });
      const updated = { ...selected, credits: result.balance_after };
      setSelected(updated);
      setUsers((current) => current.map((user) => user.id === updated.id ? updated : user));
      setState({ busy: false, error: '', result: `Credit adjustment completed. New balance: ${result.balance_after} credits.` });
      setIdempotencyKey(null);
      setAmount('');
      setReason('');
      setConfirming(false);
    } catch (error) {
      setState((current) => ({ ...current, busy: false, error: errorMessage(error) }));
    }
  }

  return <section className="page-shell narrow-shell">
    <PageIntro eyebrow="Protected administrator tool" title="Wallet adjustments" description="Search for a user and record an audited credit change."/>
    <form className="inline-search" onSubmit={search}>
      <label htmlFor="wallet-user-search">User search</label>
      <input id="wallet-user-search" minLength="2" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Username or email" required/>
      <button className="button button-light" disabled={state.busy}>Search</button>
    </form>
    {users.map((user) => <button type="button" className="wallet-user-row" key={user.id} onClick={() => {
      setSelected(user); setIdempotencyKey(null); setConfirming(false); setState({ busy: false, error: '', result: '' });
    }}>
      <strong>{user.username}</strong><span>{user.email}</span><b>{user.credits} credits</b>
    </button>)}

    {selected && <form className="editor-form" onSubmit={(event) => { event.preventDefault(); setConfirming(true); setState((current) => ({ ...current, error: '' })); }}>
      <h2>{[selected.first_name, selected.last_name].filter(Boolean).join(' ') || selected.username}</h2>
      <p>Username: <strong>{selected.username}</strong> · Role: <strong>{selected.role || 'learner'}</strong></p>
      <p>Current balance: <strong>{selected.credits} credits</strong></p>
      <fieldset>
        <legend>Adjustment</legend>
        <label><input type="radio" name="wallet-direction" value="add" checked={direction === 'add'} onChange={() => { setDirection('add'); setIdempotencyKey(null); setConfirming(false); }}/> Add credits</label>
        <label><input type="radio" name="wallet-direction" value="remove" checked={direction === 'remove'} onChange={() => { setDirection('remove'); setIdempotencyKey(null); setConfirming(false); }}/> Remove credits</label>
      </fieldset>
      <label>Amount in credits<input type="number" min="0.01" max="9999999999.99" step="0.01" required value={amount} onChange={(event) => { setAmount(event.target.value); setIdempotencyKey(null); setConfirming(false); }}/></label>
      <label>Required reason<textarea maxLength="255" required value={reason} onChange={(event) => { setReason(event.target.value); setIdempotencyKey(null); setConfirming(false); }}/></label>
      <p>New balance: <strong>{nextBalance === null ? '—' : `${fromCents(nextBalance)} credits`}</strong></p>
      {confirming ? <div className="notice" role="dialog" aria-modal="true" aria-labelledby="wallet-confirm-title">
        <h3 id="wallet-confirm-title">Confirm credit adjustment</h3>
        <p>Target: <strong>{selected.username}</strong></p>
        <p>Current balance: <strong>{selected.credits} credits</strong></p>
        <p>Adjustment: <strong>{direction === 'add' ? '+' : '−'}{amount} credits</strong></p>
        <p>Resulting balance: <strong>{nextBalance === null ? '—' : `${fromCents(nextBalance)} credits`}</strong></p>
        <p>Reason: <strong>{reason.trim()}</strong></p>
        <button type="button" className="button button-light" disabled={state.busy} onClick={() => setConfirming(false)}>Cancel</button>
        <button type="button" className="button button-primary" disabled={state.busy || !validAdjustment} onClick={adjust}>{state.busy ? 'Applying…' : 'Confirm adjustment'}</button>
      </div> : <button className="button button-primary" disabled={!validAdjustment || state.busy}>Review adjustment</button>}
    </form>}
    {state.error && <p className="notice notice-error" role="alert">{state.error}</p>}
    {state.result && <p className="notice notice-success" role="status">{state.result}</p>}
  </section>;
}
