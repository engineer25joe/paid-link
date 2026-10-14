import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAdminDashboard } from '../api/marketplace.js';
import { api } from '../api/client.js';
import { getApiErrorMessage } from '../api/errors.js';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';

// Admin dashboard uses the role-protected aggregate endpoint and links to implemented read APIs.
export function AdminPage() {
  const [stats, setStats] = useState(null);
  const [state, setState] = useState({ loading: true, error: '' });
  const [applications, setApplications] = useState([]);
  const [applicationPage, setApplicationPage] = useState({ next: null, previous: null, page: 1 });
  const [creator, setCreator] = useState({ username: '', email: '', password: '' });
  const [actionMessage, setActionMessage] = useState('');
  useEffect(() => { let active = true; getAdminDashboard().then((result) => { if (active) { setStats(result); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, []);
  useEffect(() => { api.get(`/api/admin/creator-applications/?page=${applicationPage.page}`).then((data) => { setApplications(data.results || []); setApplicationPage((current) => ({ ...current, next: data.next, previous: data.previous })); }).catch((error) => setActionMessage(getApiErrorMessage(error.data, error.message))); }, [applicationPage.page]);
  async function decide(id, status) { setActionMessage(''); try { await api.post(`/api/admin/creator-applications/${id}/decision/`, { status }); setApplications((current) => current.map((item) => item.id === id ? { ...item, status } : item)); } catch (error) { setActionMessage(getApiErrorMessage(error.data, error.message)); } }
  async function createCreator(event) { event.preventDefault(); setActionMessage(''); try { const result = await api.post('/api/admin/creators/create/', creator); setActionMessage(`Creator account ${result.username} created.`); setCreator({ username: '', email: '', password: '' }); } catch (error) { setActionMessage(getApiErrorMessage(error.data, error.message)); } }
  const links = [['Users', 'users'], ['Creators', 'creators'], ['Learners', 'learners'], ['Content', 'content'], ['Purchases', 'purchases'], ['Credit ledger', 'ledger'], ['Withdrawals', 'withdrawals'], ['Wallet adjustments', 'wallet'], ['Credit conversion', 'settings']];
  return <section className="page-shell"><PageIntro eyebrow="Admin view" title="Platform overview" description="Read-only platform metrics and protected management lists."/>
    <LoadState loading={state.loading} error={state.error}>{stats && <div className="workspace-metrics"><Metric label="Users" value={stats.total_users}/><Metric label="Learners" value={stats.learners}/><Metric label="Creators" value={stats.creators}/><Metric label="Published resources" value={stats.published_content}/><Metric label="Purchases" value={stats.total_purchases}/><Metric label="Purchase value" value={`KES ${stats.total_purchase_value}`}/><Metric label="Pending withdrawals" value={stats.pending_withdrawals}/><Metric label="Unresolved payment records" value={stats.unresolved_payment_records}/></div>}</LoadState>
    <h2 className="section-title">Management lists</h2><div className="admin-link-grid">{links.map(([label, section]) => <Link className="admin-link-card" key={section} to={`/admin/${section}`}><span>{label}</span><strong aria-hidden="true">↗</strong></Link>)}</div>
    <p><Link className="button button-light" to="/creator/shares">Share management</Link></p><h2 className="section-title">Creator applications</h2>{applications.filter((item) => item.status === 'pending').map((item) => <article className="creator-item" key={item.id}><div className="creator-item-actions"><strong>{item.username}</strong><span>{item.motivation}</span><button className="button button-light" onClick={() => decide(item.id, 'approved')}>Approve</button><button className="button button-light" onClick={() => decide(item.id, 'rejected')}>Reject</button></div></article>)}{!applications.some((item) => item.status === 'pending') && <p>No pending applications on this page.</p>}<div className="pagination"><button className="button button-light" disabled={!applicationPage.previous} onClick={() => setApplicationPage((current) => ({ ...current, page: current.page - 1 }))}>Previous applications</button><span>Page {applicationPage.page}</span><button className="button button-light" disabled={!applicationPage.next} onClick={() => setApplicationPage((current) => ({ ...current, page: current.page + 1 }))}>More applications</button></div>
    <form className="auth-form" onSubmit={createCreator}><h2>Create creator account</h2><p>Provide an initial password securely to the new creator; it is stored only as a password hash.</p><label>Username<input required value={creator.username} onChange={(event) => setCreator({ ...creator, username: event.target.value })}/></label><label>Email<input type="email" required value={creator.email} onChange={(event) => setCreator({ ...creator, email: event.target.value })}/></label><label>Initial password<input type="password" minLength="14" required value={creator.password} onChange={(event) => setCreator({ ...creator, password: event.target.value })}/></label><button className="button button-primary">Create creator</button>{actionMessage && <p role="status">{actionMessage}</p>}</form>
    <p className="fine-print">Withdrawal review is supported. Provider payout submission and payment reconciliation are intentionally not exposed here.</p>
  </section>;
}
function Metric({ label, value }) { return <div className="workspace-metric"><span>{label}</span><strong>{value ?? '—'}</strong></div>; }
