import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getAdminDashboard } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';

// Admin dashboard uses the role-protected aggregate endpoint and links to implemented read APIs.
export function AdminPage() {
  const [stats, setStats] = useState(null);
  const [state, setState] = useState({ loading: true, error: '' });
  useEffect(() => { let active = true; getAdminDashboard().then((result) => { if (active) { setStats(result); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, []);
  const links = [['Users', 'users'], ['Creators', 'creators'], ['Learners', 'learners'], ['Content', 'content'], ['Purchases', 'purchases'], ['Credit ledger', 'ledger'], ['Withdrawals', 'withdrawals']];
  return <section className="page-shell"><PageIntro eyebrow="Admin view" title="Platform overview" description="Read-only platform metrics and protected management lists."/>
    <LoadState loading={state.loading} error={state.error}>{stats && <div className="workspace-metrics"><Metric label="Users" value={stats.total_users}/><Metric label="Learners" value={stats.learners}/><Metric label="Creators" value={stats.creators}/><Metric label="Published resources" value={stats.published_content}/><Metric label="Purchases" value={stats.total_purchases}/><Metric label="Purchase value" value={`${stats.total_purchase_value} credits`}/><Metric label="Pending withdrawals" value={stats.pending_withdrawals}/><Metric label="Unresolved payment records" value={stats.unresolved_payment_records}/></div>}</LoadState>
    <h2 className="section-title">Management lists</h2><div className="admin-link-grid">{links.map(([label, section]) => <Link className="admin-link-card" key={section} to={`/admin/${section}`}><span>{label}</span><strong aria-hidden="true">↗</strong></Link>)}</div>
    <p className="fine-print">Withdrawal review is supported. Provider payout submission and payment reconciliation are intentionally not exposed here.</p>
  </section>;
}
function Metric({ label, value }) { return <div className="workspace-metric"><span>{label}</span><strong>{value ?? '—'}</strong></div>; }
