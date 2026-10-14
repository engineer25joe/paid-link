import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { getApiErrorMessage } from '../api/errors.js';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';

export function PurchasesPage({ library = false }) {
  const [items, setItems] = useState([]);
  const [state, setState] = useState({ loading: true, error: '' });
  useEffect(() => { let active = true; api.get(API_PATHS.myPurchases).then((data) => { if (active) { setItems(data); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, []);
  return <section className="page-shell"><PageIntro eyebrow={library ? 'My library' : 'My purchases'} title={library ? 'Your learning collection' : 'Purchase history'} description="Your purchased resources, loaded securely from your account."/><LoadState loading={state.loading} error={state.error}>{items.length ? <div className="creator-content-grid">{items.map((item) => <article className="creator-item" key={item.id}><div className="content-card"><h2>{item.title}</h2><p>{item.description}</p><div className="content-meta"><span>{item.content_type}</span><span>KES {item.price_kes ?? item.amount_paid}</span><span>{item.credits_charged ?? item.price} credits</span></div><p className="fine-print">Purchased {new Date(item.purchased_at).toLocaleDateString()} at 1 credit = KES {item.conversion_rate ?? '—'}</p><Link to={`/content/${item.content_id}`}>Open resource</Link></div></article>)}</div> : <div className="empty-panel"><h2>No purchases yet</h2><p>Browse the catalogue to find a resource for your studies.</p><Link className="button button-primary" to="/explore">Explore resources</Link></div>}</LoadState></section>;
}
