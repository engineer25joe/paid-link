import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { getMyContent, updateContent, setContentPublished } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';

// Updates only fields accepted by the documented PATCH endpoints; files cannot be replaced here.
export function EditContentPage() {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [state, setState] = useState({ loading: true, error: '' });
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  useEffect(() => { let active = true; getMyContent().then((result) => { if (active) { setItem(result.find((row) => String(row.id) === id) || null); setState({ loading: false, error: '' }); } }).catch((error) => { if (active) setState({ loading: false, error: getApiErrorMessage(error.data, error.message) }); }); return () => { active = false; }; }, [id]);
  async function submit(event) { event.preventDefault(); setBusy(true); setState((current) => ({ ...current, error: '' })); const form = new FormData(event.currentTarget); const changes = Object.fromEntries(['title', 'description', 'price', 'thumbnail_url'].map((key) => [key, form.get(key)])); try { await updateContent(id, changes); navigate('/creator/content', { replace: true }); } catch (error) { setState((current) => ({ ...current, error: getApiErrorMessage(error.data, error.message) })); } finally { setBusy(false); } }
  async function togglePublish() { setBusy(true); try { const result = await setContentPublished(id, !item.is_published); setItem(result.content); } catch (error) { setState((current) => ({ ...current, error: getApiErrorMessage(error.data, error.message) })); } finally { setBusy(false); } }
  return <section className="page-shell narrow-shell"><Link className="back-link" to="/creator/content">← My content</Link><PageIntro eyebrow="Creator studio" title="Edit content" description="Update catalogue details or change publication status."/>
    <LoadState loading={state.loading} error={state.error} empty={item ? '' : 'This content was not found in your creator workspace.'}>{item && <><form className="editor-form" onSubmit={submit}><label>Title<input name="title" defaultValue={item.title} required/></label><label>Description<textarea name="description" rows="5" defaultValue={item.description} required/></label><label>Price in credits<input name="price" type="number" min="0.01" step="0.01" defaultValue={item.price} required/></label><label>Thumbnail URL<input name="thumbnail_url" type="url" defaultValue={item.thumbnail_url || ''}/></label><button className="button button-primary" disabled={busy}>{busy ? 'Saving…' : 'Save changes'}</button></form><div className="publish-control"><span>Current status: <strong>{item.is_published ? 'Published' : 'Draft'}</strong></span><button className="button button-light" onClick={togglePublish} disabled={busy}>{item.is_published ? 'Unpublish' : 'Publish'}</button></div></>}</LoadState>
  </section>;
}
