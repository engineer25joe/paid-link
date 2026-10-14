import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { getContentAccess, purchaseContent } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { usePublicContent } from '../hooks/usePublicContent.js';
import { APP_NAME } from '../config/brand.js';
import { findContent, getAuthorizedContent, getContentAccessError } from './contentDetailState.js';

// Catalogue metadata is public; the actual file is rendered only from the
// short-lived URL returned after the backend verifies the signed-in owner.
export function ContentDetailPage() {
  const { id } = useParams();
  const { user, refreshProfile } = useAuth();
  const { items, loading, error: listError } = usePublicContent();
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [accessState, setAccessState] = useState('idle');
  const [purchaseStatus, setPurchaseStatus] = useState('idle');
  const [protectedContent, setProtectedContent] = useState(null);
  const [viewerError, setViewerError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();
  const item = findContent(items, id);

  function signIn() {
    navigate('/login', { state: { from: { pathname: location.pathname } } });
  }

  async function accessContent() {
    if (!user) { setAccessState('authentication-required'); return; }
    setBusy('access'); setError(''); setViewerError(''); setProtectedContent(null);
    try {
      const content = getAuthorizedContent(await getContentAccess(id));
      setProtectedContent(content);
      setAccessState('access-granted');
    } catch (failure) {
      const result = getContentAccessError(failure);
      setAccessState(result.state);
      setError(result.state === 'network-error' ? result.message : (failure instanceof Error && !failure.status ? failure.message : getApiErrorMessage(failure.data, result.message)));
    } finally { setBusy(''); }
  }

  async function buyContent() {
    if (!user) { setAccessState('authentication-required'); return; }
    setBusy('purchase'); setError(''); setMessage(''); setProtectedContent(null); setAccessState('idle');
    try {
      const result = await purchaseContent(id);
      setPurchaseStatus('purchase-successful');
      setMessage(`Purchase complete. Your remaining balance is ${result.remaining_credits} credits.`);
      try { await refreshProfile(); } catch { setMessage('Purchase complete. Your displayed balance could not be refreshed; the server balance remains authoritative.'); }
      // Fetch the file URL only after the purchase endpoint confirms success.
      await accessContent();
    } catch (failure) {
      setAccessState(failure?.status === 401 ? 'authentication-required' : 'idle');
      setError(getApiErrorMessage(failure.data, failure.message || 'The purchase could not be completed. Please try again.'));
    } finally { setBusy(''); }
  }

  const backLink = <Link className="back-link" to="/explore">← Back to Explore</Link>;
  if (loading) return <section className="page-shell detail-shell">{backLink}<p className="notice" role="status">Loading resource details…</p></section>;
  if (listError) return <section className="page-shell detail-shell">{backLink}<div className="notice notice-error" role="alert"><h1>We couldn’t load this resource</h1><p>{listError}</p><Link className="button button-light" to="/explore">Return to Explore</Link></div></section>;
  if (!item) return <section className="page-shell detail-shell">{backLink}<div className="notice" role="status"><h1>Resource not found</h1><p>This resource is unavailable or has been unpublished.</p><Link className="button button-light" to="/explore">Browse available resources</Link></div></section>;
  if (!['pdf', 'video'].includes(item.content_type)) return <section className="page-shell detail-shell">{backLink}<div className="notice notice-error" role="alert"><h1>Unsupported resource type</h1><p>This resource type cannot be opened here. Please return to Explore.</p><Link className="button button-light" to="/explore">Return to Explore</Link></div></section>;

  return <section className="page-shell detail-shell">
    {backLink}
    <article className="detail-card">
      <div className={`detail-art content-art-${item.content_type}`} aria-hidden="true"><span>{item.content_type === 'video' ? '▶' : 'PDF'}</span></div>
      <div className="detail-copy">
        <div className="content-meta"><span>{item.content_type}</span>{item.creator_username && <span>By {item.creator_username}</span>}</div>
        <h1>{item.title || 'Untitled resource'}</h1>
        {item.description && <p>{item.description}</p>}
        <div className="detail-price"><span>One-time price</span><strong>KES {item.price_kes ?? '—'} · {item.price ?? '—'} credits</strong></div>
        {error && <div className="notice notice-error" role="alert"><p>{error}</p>{accessState === 'authentication-required' && <button className="button button-light" onClick={signIn}>Sign in to continue</button>}{accessState === 'not-found' && <Link className="button button-light" to="/explore">Browse available resources</Link>}</div>}
        {message && <p className="notice notice-success" role="status">{message}</p>}
        {accessState === 'purchase-required' && <p className="notice" role="status">Purchase required: complete the purchase below to unlock this resource.</p>}
        {purchaseStatus === 'purchase-successful' && <p className="notice notice-success" role="status">Purchase successful. The server confirmed payment in credits; protected file access is checked separately.</p>}
        <div className="detail-actions">
          {!user ? <button className="button button-primary" onClick={signIn}>Sign in to purchase or access</button> : <>
            <button className="button button-primary" onClick={buyContent} disabled={Boolean(busy)}>{busy === 'purchase' ? 'Processing…' : 'Purchase resource'}</button>
            <button className="button button-light" onClick={accessContent} disabled={Boolean(busy)}>{busy === 'access' ? 'Checking access…' : 'Open my resource'}</button>
          </>}
        </div>
        {protectedContent && <section className="protected-viewer" aria-label="Authorized resource">
          <h2>Your resource is ready</h2>
          {protectedContent.content_type === 'pdf' ? <>
            <iframe title={`PDF: ${item.title || 'resource'}`} src={protectedContent.file_url} className="pdf-viewer" onError={() => setViewerError('This browser could not display the PDF inline. Use the secure open button below.')} />
            <p className="fine-print">If the viewer is blank or unsupported in your browser, open the time-limited protected PDF directly.</p>
          </> : <video className="video-viewer" controls playsInline preload="metadata" src={protectedContent.file_url} onLoadStart={() => setViewerError('')} onError={() => setViewerError('The video could not be loaded. The secure open link below may work in another player.')} />}
          {viewerError && <p className="notice notice-error" role="alert">{viewerError}</p>}
          <a className="button button-secondary" href={protectedContent.file_url} target="_blank" rel="noopener noreferrer">Open protected resource in a new tab ↗</a>
        </section>}
        <p className="fine-print">Purchases and file access are verified by the {APP_NAME} backend. Your balance is not changed unless the API confirms the purchase.</p>
      </div>
    </article>
  </section>;
}
