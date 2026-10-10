import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getMyContent, setContentPublished } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { ContentCard } from '../components/ContentCard.jsx';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';

// Creator workspace lists only the authenticated creator's own content from the API.
export function CreatorContentPage() {
  const [items, setItems] = useState([]);
  const [state, setState] = useState({ loading: true, error: '' });
  const [busyId, setBusyId] = useState(null);
  useEffect(() => {
    let active = true;
    getMyContent().then((result) => { if (active) { setItems(Array.isArray(result) ? result : []); setState({ loading: false, error: '' }); } })
      .catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); });
    return () => { active = false; };
  }, []);
  async function togglePublish(item) {
    setBusyId(item.id); setState((current) => ({ ...current, error: '' }));
    try { const result = await setContentPublished(item.id, !item.is_published); setItems((current) => current.map((row) => row.id === item.id ? result.content : row)); }
    catch (error) { setState((current) => ({ ...current, error: getApiErrorMessage(error.data, error.message) })); }
    finally { setBusyId(null); }
  }
  return <section className="page-shell"><PageIntro eyebrow="Creator studio" title="My content" description="Manage your learning resources and publication status." action={<Link className="button button-primary" to="/creator/content/new">Create content <span aria-hidden="true">＋</span></Link>}/>
    <LoadState loading={state.loading} error={state.error} empty={items.length ? '' : 'You have not created any resources yet.'}>
      <div className="creator-content-grid">{items.map((item) => <article className="creator-item" key={item.id}><ContentCard item={item} manage/><div className="creator-item-actions"><span className={`status-pill ${item.is_published ? 'status-live' : ''}`}>{item.is_published ? 'Published' : 'Draft'}</span><button className="text-action" onClick={() => togglePublish(item)} disabled={busyId === item.id}>{busyId === item.id ? 'Saving…' : item.is_published ? 'Unpublish' : 'Publish'}</button></div></article>)}</div>
    </LoadState>
  </section>;
}
