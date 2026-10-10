import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ADMIN_LIST_ENDPOINTS, getAdminList, runAdminWithdrawalAction } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';

const sections = {
  users: { title: 'Users', endpoint: ADMIN_LIST_ENDPOINTS.users, columns: ['username', 'email', 'role', 'credits', 'is_active'] },
  creators: { title: 'Creators', endpoint: ADMIN_LIST_ENDPOINTS.creators, columns: ['username', 'email', 'credits', 'is_verified'] },
  learners: { title: 'Learners', endpoint: ADMIN_LIST_ENDPOINTS.learners, columns: ['username', 'email', 'credits', 'is_verified'] },
  content: { title: 'Content', endpoint: ADMIN_LIST_ENDPOINTS.content, columns: ['title', 'creator_username', 'content_type', 'price', 'is_published'] },
  purchases: { title: 'Purchases', endpoint: ADMIN_LIST_ENDPOINTS.purchases, columns: ['user_username', 'content_title', 'amount_paid', 'purchased_at'] },
  ledger: { title: 'Credit ledger', endpoint: ADMIN_LIST_ENDPOINTS.ledger, columns: ['user_username', 'transaction_type', 'amount', 'balance_after', 'created_at'] },
  withdrawals: { title: 'Withdrawals', endpoint: ADMIN_LIST_ENDPOINTS.withdrawals, columns: ['creator_username', 'amount', 'status', 'payout_status', 'phone_number', 'created_at'] },
};

// Tables render only fields allowed by the existing admin API; withdrawal actions call its admin endpoints.
export function AdminListPage() {
  const { section } = useParams();
  const config = sections[section];
  const [payload, setPayload] = useState({ results: [], count: 0, next: null, previous: null });
  const [page, setPage] = useState(1);
  const [state, setState] = useState({ loading: Boolean(config), error: '' });
  const [actionBusy, setActionBusy] = useState(null);
  const [notice, setNotice] = useState('');
  useEffect(() => {
    if (!config) return undefined;
    let active = true;
    setState({ loading: true, error: '' });
    getAdminList(`${config.endpoint}?page=${page}`).then((result) => { if (active) { setPayload(result); setState({ loading: false, error: '' }); } })
      .catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); });
    return () => { active = false; };
  }, [config, page]);
  async function withdrawalAction(row, action) {
    const message = action === 'approve' ? `Approve withdrawal #${row.id}? This reserves ${row.amount} credits from the creator.` : `Cancel withdrawal #${row.id}?`;
    if (!window.confirm(message)) return;
    setActionBusy(row.id); setNotice(''); setState((current) => ({ ...current, error: '' }));
    try { await runAdminWithdrawalAction(row.id, action); setNotice(`Withdrawal #${row.id} updated.`); const refreshed = await getAdminList(`${config.endpoint}?page=${page}`); setPayload(refreshed); }
    catch (error) { setState((current) => ({ ...current, error: getApiErrorMessage(error.data, error.message) })); }
    finally { setActionBusy(null); }
  }
  if (!config) return <section className="page-shell"><PageIntro eyebrow="Admin view" title="List unavailable" description="Choose a management list from the admin overview."/><Link to="/admin">Back to overview</Link></section>;
  return <section className="page-shell"><Link className="back-link" to="/admin">← Admin overview</Link><PageIntro eyebrow="Admin view" title={config.title} description={`${payload.count} records returned by the protected admin API.`}/>
    {notice && <p className="notice notice-success" role="status">{notice}</p>}
    <LoadState loading={state.loading} error={state.error} empty={payload.results.length ? '' : 'No records to show.'}><div className="table-wrap"><table><thead><tr>{config.columns.map((column) => <th key={column}>{column.replaceAll('_', ' ')}</th>)}{(section === 'withdrawals' || section === 'content') && <th>Actions</th>}</tr></thead><tbody>{payload.results.map((row) => <tr key={row.id}>{config.columns.map((column) => <td key={column}>{formatValue(row[column])}</td>)}{section === 'withdrawals' && <td><div className="table-actions">{row.status === 'pending' && <button className="text-action" onClick={() => withdrawalAction(row, 'approve')} disabled={actionBusy === row.id}>Approve</button>}{['pending', 'approved_reserved'].includes(row.status) && <button className="text-action text-danger" onClick={() => withdrawalAction(row, 'cancel')} disabled={actionBusy === row.id}>Cancel</button>}</div></td>}{section === 'content' && <td><Link className="text-action" to={`/admin/content/${row.id}/edit`}>Edit</Link></td>}</tr>)}</tbody></table></div></LoadState>
    <div className="pagination"><button className="button button-light" onClick={() => setPage((value) => value - 1)} disabled={!payload.previous || state.loading}>Previous</button><span>Page {page}</span><button className="button button-light" onClick={() => setPage((value) => value + 1)} disabled={!payload.next || state.loading}>Next</button></div>
  </section>;
}

function formatValue(value) { if (typeof value === 'boolean') return value ? 'Yes' : 'No'; if (value == null || value === '') return '—'; if (typeof value === 'object') return '—'; return String(value); }
