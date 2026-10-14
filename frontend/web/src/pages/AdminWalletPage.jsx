import { useState } from 'react';
import { api } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { getApiErrorMessage } from '../api/errors.js';
import { PageIntro } from '../components/PageIntro.jsx';

export function AdminWalletPage() {
  const [query, setQuery] = useState(''); const [users, setUsers] = useState([]); const [selected, setSelected] = useState(null);
  const [direction, setDirection] = useState('add'); const [amount, setAmount] = useState(''); const [reason, setReason] = useState('');
  const [confirming, setConfirming] = useState(false); const [state, setState] = useState({ busy: false, error: '', result: '' });
  async function search(event) { event.preventDefault(); setSelected(null); setState({ busy: false, error: '', result: '' }); try { const data = await api.get(`${API_PATHS.adminWalletUsers}?search=${encodeURIComponent(query)}`); setUsers(data.results || []); } catch (error) { setState((s) => ({ ...s, error: getApiErrorMessage(error.data, error.message) })); } }
  async function adjust() { setState((s) => ({ ...s, busy: true, error: '', result: '' })); try { const result = await api.post(`/api/admin/wallet/users/${selected.id}/adjust/`, { direction, amount, reason, idempotency_key: crypto.randomUUID() }); setState((s) => ({ ...s, result: `${result.status}: ${result.user} balance ${result.balance_before} → ${result.balance_after} credits.` })); setSelected({ ...selected, credits: result.balance_after }); setAmount(''); setReason(''); setConfirming(false); } catch (error) { setState((s) => ({ ...s, error: getApiErrorMessage(error.data, error.message) })); } finally { setState((s) => ({ ...s, busy: false })); } }
  return <section className="page-shell narrow-shell"><PageIntro eyebrow="Protected administrator tool" title="Wallet adjustments" description="Search for a user and record an audited credit change."/>
    <form className="inline-search" onSubmit={search}><label htmlFor="wallet-user-search">User search</label><input id="wallet-user-search" minLength="2" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Username or email" required/><button className="button button-light">Search</button></form>
    {users.map((user) => <button type="button" className="wallet-user-row" key={user.id} onClick={() => { setSelected(user); setConfirming(false); }}><strong>{user.username}</strong><span>{user.email}</span><b>{user.credits} credits</b></button>)}
    {selected && <form className="editor-form" onSubmit={(e) => { e.preventDefault(); setConfirming(true); }}><h2>{selected.username}</h2><p>Current balance: <strong>{selected.credits} credits</strong></p>
      <label>Action<select value={direction} onChange={(e) => setDirection(e.target.value)}><option value="add">Add credits</option><option value="remove">Remove credits</option></select></label>
      <label>Amount in credits<input type="number" min="0.01" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)}/></label>
      <label>Required reason<textarea maxLength="255" required value={reason} onChange={(e) => setReason(e.target.value)}/></label>
      {confirming ? <div className="notice" role="alert"><p>Confirm {direction} of {amount} credits for {selected.username}?</p><button type="button" className="button button-light" onClick={() => setConfirming(false)}>Cancel</button><button type="button" className="button button-primary" disabled={state.busy} onClick={adjust}>Confirm adjustment</button></div> : <button className="button button-primary">Review adjustment</button>}
    </form>}
    {state.error && <p className="notice notice-error" role="alert">{state.error}</p>}{state.result && <p className="notice notice-success" role="status">{state.result}</p>}
  </section>;
}
