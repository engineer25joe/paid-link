import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { getApiErrorMessage } from '../api/errors.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { dashboardPath } from '../auth/navigation.js';

const workspaceInfo = {
  learner: { title: 'Your learning space', description: 'Discover published resources and continue building your library.', links: [['Explore resources', '/explore'], ['My library', null]] },
  creator: { title: 'Your creator space', description: 'Review your content and explore the learning catalogue.', links: [['Explore resources', '/explore']] },
  admin: { title: 'Platform overview', description: 'A quick view of platform activity for administrators.', links: [['Explore resources', '/explore']] },
};

function Metric({ label, value }) { return <div className="workspace-metric"><span>{label}</span><strong>{value ?? '—'}</strong></div>; }

export function WorkspacePage() {
  const { user } = useAuth();
  const info = workspaceInfo[user?.role];
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    const request = user?.role === 'creator' ? API_PATHS.myContent : user?.role === 'admin' ? API_PATHS.adminDashboard : null;
    if (!request) { setData(null); setError(''); return () => { active = false; }; }
    api.get(request).then((result) => { if (active) { setData(result); setError(''); } })
      .catch((failure) => { if (active) setError(getApiErrorMessage(failure.data, failure.message)); });
    return () => { active = false; };
  }, [user?.role]);
  if (!info) return <section className="placeholder"><div className="eyebrow">Workspace unavailable</div><h1>We could not identify your role</h1><p>Sign out and log in again, or contact support.</p></section>;
  return <section className="workspace"><div className="eyebrow">{user.role}</div><h1>{info.title}</h1><p>{info.description}</p>
    <div className="workspace-links">{info.links.map(([label, path]) => <article className="workspace-link" key={label}><h2>{label}</h2>{path ? <Link to={path}>Open {label.toLowerCase()} →</Link> : <><p>This feature is coming soon.</p><span className="coming-soon">Coming soon</span></>}</article>)}</div>
    {error && <p className="form-error" role="alert">Could not load workspace data: {error}</p>}
    {user.role === 'creator' && Array.isArray(data) && <section aria-label="My content"><h2>My content</h2>{data.length ? <div className="workspace-links">{data.map((item) => <article className="workspace-link" key={item.id}><span className="eyebrow">{item.is_published ? 'Published' : 'Draft'} · {item.content_type}</span><h3>{item.title}</h3><p>{item.description}</p><strong>{item.price} credits</strong></article>)}</div> : <p>You have not added any content yet.</p>}<p className="muted-copy">Content management is coming soon.</p></section>}
    {user.role === 'admin' && data && <section aria-label="Platform activity"><h2>Platform activity</h2><div className="workspace-metrics"><Metric label="Users" value={data.total_users}/><Metric label="Learners" value={data.learners}/><Metric label="Creators" value={data.creators}/><Metric label="Published content" value={data.published_content}/><Metric label="Purchases" value={data.total_purchases}/><Metric label="Pending withdrawals" value={data.pending_withdrawals}/></div><p className="muted-copy">Management tools are coming soon.</p></section>}
    <Link className="secondary-link" to={dashboardPath(user.role)}>Return to dashboard</Link></section>;
}
