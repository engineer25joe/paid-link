import { useEffect, useState } from 'react';
import { getCreatorContentEarnings, getCreatorEarnings } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';

// Sales figures come directly from the creator-scoped earnings endpoints.
export function CreatorEarningsPage() {
  const [summary, setSummary] = useState(null);
  const [byContent, setByContent] = useState([]);
  const [state, setState] = useState({ loading: true, error: '' });
  useEffect(() => { let active = true; Promise.all([getCreatorEarnings(), getCreatorContentEarnings()]).then(([stats, rows]) => { if (active) { setSummary(stats); setByContent(rows); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, []);
  return <section className="page-shell"><PageIntro eyebrow="Creator studio" title="Earnings" description="Sales and balances reported by the creator earnings API."/>
    <LoadState loading={state.loading} error={state.error}>{summary && <><div className="workspace-metrics"><Metric label="Sales" value={summary.total_sales_count}/><Metric label="Gross earnings" value={`${summary.gross_earnings} credits`}/><Metric label="Available credits" value={summary.available_credit_balance}/><Metric label="Published resources" value={summary.published_contents_count}/></div><div className="table-wrap"><table><thead><tr><th>Resource</th><th>Price</th><th>Purchases</th><th>Gross sales</th></tr></thead><tbody>{byContent.map((row) => <tr key={row.content_id}><td>{row.title}</td><td>{row.price}</td><td>{row.purchase_count}</td><td>{row.gross_sales}</td></tr>)}</tbody></table></div><p className="fine-print">Withdrawals are reviewed separately. No payout action is performed here.</p></>}</LoadState>
  </section>;
}
function Metric({ label, value }) { return <div className="workspace-metric"><span>{label}</span><strong>{value ?? '—'}</strong></div>; }
