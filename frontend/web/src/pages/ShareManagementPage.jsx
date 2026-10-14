import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createShare, getShares, getPublicContent, revokeShare } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { PageIntro } from '../components/PageIntro.jsx';
import { useCountdown } from '../hooks/useCountdown.js';

function ShareRow({ item, onRevoke }) {
  const countdown = useCountdown(item.expires_at);
  const [copied, setCopied] = useState(false);
  async function copy() { try { await navigator.clipboard.writeText(item.share_url); setCopied(true); } catch { setCopied(false); } }
  const status = countdown.expired && item.status === 'ACTIVE' ? 'EXPIRED' : item.status;
  return <article className="share-row"><div><h3>{item.content_title}</h3><p>{item.share_url}</p><dl><dt>Created by</dt><dd>{item.created_by} · {new Date(item.created_at).toLocaleString()}</dd><dt>Expires</dt><dd>{new Date(item.expires_at).toLocaleString()} · {countdown.expired ? 'Expired' : countdown.label}</dd><dt>Uses</dt><dd>{item.successful_uses}/{item.max_uses} successful · {item.remaining_uses} remaining</dd></dl><strong className={`share-status ${status === 'ACTIVE' ? 'is-active' : ''}`}>{status}</strong></div><div className="detail-actions"><button className="button button-light" onClick={copy}>{copied ? 'Copied' : 'Copy link'}</button>{status !== 'REVOKED' && <button className="button button-light" onClick={() => onRevoke(item.id)}>Revoke link</button>}</div></article>;
}

export function ShareManagementPage() {
  const [content, setContent] = useState([]); const [shares, setShares] = useState([]); const [selected, setSelected] = useState('');
  const [hours, setHours] = useState('2'); const [uses, setUses] = useState('2'); const [state, setState] = useState({ loading: true, busy: false, error: '', notice: '' });
  const refresh = useCallback(async () => { const rows = await getShares(); setShares(rows.results || []); }, []);
  useEffect(() => { let active = true; Promise.all([getPublicContent(), getShares()]).then(([items, rows]) => { if (active) { setContent(items.filter((item) => item.is_published)); setShares(rows.results || []); setState((s) => ({ ...s, loading: false })); } }).catch((error) => { if (active) setState((s) => ({ ...s, loading: false, error: getApiErrorMessage(error.data, error.message) })); }); return () => { active = false; }; }, []);
  useEffect(() => { const timer = window.setInterval(() => refresh().catch(() => {}), 15000); return () => window.clearInterval(timer); }, [refresh]);
  async function create(event) { event.preventDefault(); setState((s) => ({ ...s, busy: true, error: '', notice: '' })); try { const result = await createShare({ content_id: selected, expires_in_hours: hours, max_uses: uses, access_duration_hours: 2 }); setShares((rows) => [result, ...rows]); setState((s) => ({ ...s, notice: `Share created. Its payment link expires in ${hours} hour(s); guest access lasts 2 hours after verified payment.` })); } catch (error) { setState((s) => ({ ...s, error: getApiErrorMessage(error.data, error.message) })); } finally { setState((s) => ({ ...s, busy: false })); } }
  async function remove(id) { if (!window.confirm('Revoke this link? New guest payment and existing guest access will stop.')) return; try { await revokeShare(id); await refresh(); } catch (error) { setState((s) => ({ ...s, error: getApiErrorMessage(error.data, error.message) })); } }
  return <section className="page-shell"><PageIntro eyebrow="Creator tools" title="Share management" description="Share published resources with guests. Links expire after two hours by default; verified guest access lasts two hours."/>
    <form className="editor-form share-create-form" onSubmit={create}><h2>Create a guest link</h2><label>Published content<select required value={selected} onChange={(e) => setSelected(e.target.value)}><option value="">Choose content</option>{content.map((item) => <option key={item.id} value={item.id}>{item.title} · KES {item.price_kes}</option>)}</select></label><div className="form-row"><label>Share link expires in hours<input type="number" min="0.25" max="720" step="0.25" value={hours} onChange={(e) => setHours(e.target.value)} required/><span className="field-hint">Default: 2 hours from creation.</span></label><label>Maximum purchases<input type="number" min="1" max="1000" step="1" value={uses} onChange={(e) => setUses(e.target.value)} required/><span className="field-hint">Successful purchases; default: 2.</span></label></div><button className="button button-primary" disabled={state.busy || !selected}>{state.busy ? 'Creating…' : 'Share Content'}</button></form>
    {state.error && <p className="notice notice-error" role="alert">{state.error}</p>}{state.notice && <p className="notice notice-success" role="status">{state.notice}</p>}
    <h2 className="section-title">Your share links</h2>{state.loading && <p className="notice" role="status">Loading shares…</p>}{!state.loading && !shares.length && <p className="notice">No share links yet.</p>}{shares.map((item) => <ShareRow key={item.id} item={item} onRevoke={remove}/>)}
    <Link to="/creator/content">Back to your content</Link>
  </section>;
}
