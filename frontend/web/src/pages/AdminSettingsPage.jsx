import { useEffect, useState } from 'react';
import { api } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { getApiErrorMessage } from '../api/errors.js';
import { PageIntro } from '../components/PageIntro.jsx';

export function AdminSettingsPage() {
  const [rate, setRate] = useState(''); const [history, setHistory] = useState([]); const [state, setState] = useState({ loading: true, busy: false, error: '', notice: '' });
  async function load() { const result = await api.get(API_PATHS.adminCreditRate); setRate(result.rate); setHistory(result.history || []); }
  useEffect(() => { let active = true; load().then(() => { if (active) setState((s) => ({ ...s, loading: false })); }).catch((error) => { if (active) setState((s) => ({ ...s, loading: false, error: getApiErrorMessage(error.data, error.message) })); }); return () => { active = false; }; }, []);
  async function save(event) { event.preventDefault(); setState((s) => ({ ...s, busy: true, error: '', notice: '' })); try { const result = await api.put(API_PATHS.adminCreditRate, { rate }); setState((s) => ({ ...s, notice: `Rate saved: 1 credit = KES ${result.rate}. Historical purchases and top-ups are unchanged.` })); await load(); } catch (error) { setState((s) => ({ ...s, error: getApiErrorMessage(error.data, error.message) })); } finally { setState((s) => ({ ...s, busy: false })); } }
  return <section className="page-shell narrow-shell"><PageIntro eyebrow="Platform configuration" title="Credit conversion rate" description="Set how many Kenyan shillings equal one credit. Past transactions keep their recorded rate."/>
    {state.loading ? <p className="notice" role="status">Loading current rate…</p> : <form className="editor-form" onSubmit={save}><label>1 credit = KES<input type="number" required min="0.0001" step="0.0001" value={rate} onChange={(e) => setRate(e.target.value)}/></label><button className="button button-primary" disabled={state.busy}>{state.busy ? 'Saving…' : 'Save conversion rate'}</button></form>}
    {state.error && <p className="notice notice-error" role="alert">{state.error}</p>}{state.notice && <p className="notice notice-success" role="status">{state.notice}</p>}
    <h2 className="section-title">Rate history</h2><div className="table-wrap"><table><thead><tr><th>KES per credit</th><th>Changed by</th><th>Changed at</th></tr></thead><tbody>{history.map((row, index) => <tr key={`${row.created_at}-${index}`}><td>{row.rate}</td><td>{row.changed_by}</td><td>{new Date(row.created_at).toLocaleString()}</td></tr>)}{!history.length && <tr><td colSpan="3">No changes recorded yet.</td></tr>}</tbody></table></div>
  </section>;
}
