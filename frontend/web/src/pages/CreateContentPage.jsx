import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createContent } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { PageIntro } from '../components/PageIntro.jsx';

// Sends the documented multipart payload; a successful state appears only after a 201 response.
export function CreateContentPage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  async function submit(event) {
    event.preventDefault(); setBusy(true); setError('');
    try { await createContent(new FormData(event.currentTarget)); navigate('/creator/content', { replace: true }); }
    catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(false); }
  }
  return <section className="page-shell narrow-shell"><Link className="back-link" to="/creator/content">← My content</Link><PageIntro eyebrow="Creator studio" title="Create content" description="Upload a PDF guide or video lesson. New uploads remain drafts unless published."/>
    <form className="editor-form" onSubmit={submit}><label>Title<input name="title" maxLength="200" required/></label><label>Description<textarea name="description" rows="5" required/></label><div className="form-row"><label>Format<select name="content_type" required><option value="pdf">PDF guide</option><option value="video">Video</option></select></label><label>Price in credits<input name="price" type="number" min="0.01" step="0.01" required/></label></div><label>Thumbnail URL <span className="field-hint">Optional. Use a publicly available image URL.</span><input name="thumbnail_url" type="url"/></label><label>Learning file<input name="file" type="file" accept="application/pdf,video/*" required/></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="button button-primary" disabled={busy}>{busy ? 'Uploading…' : 'Upload as draft'}</button></form>
  </section>;
}
