import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { API_PATHS } from '../api/config.js';
import { getApiErrorMessage } from '../api/errors.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { dashboardPath } from '../auth/navigation.js';

export function ExplorePage() {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [state, setState] = useState({ loading: true, error: '' });
  useEffect(() => {
    let active = true;
    api.get(API_PATHS.content, { authenticated: false }).then((data) => {
      if (active) { setItems(Array.isArray(data) ? data : []); setState({ loading: false, error: '' }); }
    }).catch((error) => {
      if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) });
    });
    return () => { active = false; };
  }, []);
  return <section className="catalogue">
    <div className="eyebrow">Explore</div><h1>Learning resources</h1>
    <p>Browse published resources shared by Paid Link creators.</p>
    {state.loading && <p role="status">Loading resources…</p>}
    {state.error && <p className="form-error" role="alert">Could not load resources: {state.error}</p>}
    {!state.loading && !state.error && items.length === 0 && <p>No resources have been published yet.</p>}
    <div className="catalogue-grid">{items.map((item) => <article className="catalogue-card" key={item.id}>
      <span className="eyebrow">{item.content_type} · {item.creator_username}</span><h2>{item.title}</h2><p>{item.description}</p>
      <div className="catalogue-card-foot"><strong>{item.price} credits</strong>{user ? <Link to={dashboardPath(user.role)}>Go to workspace</Link> : <Link to="/login">Log in to continue</Link>}</div>
    </article>)}</div>
  </section>;
}
