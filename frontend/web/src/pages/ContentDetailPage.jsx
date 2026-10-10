import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { getContentAccess, purchaseContent } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { useAuth } from '../auth/AuthContext.jsx';
import { usePublicContent } from '../hooks/usePublicContent.js';
import { LoadState } from '../components/LoadState.jsx';
import { APP_NAME } from '../config/brand.js';

// Details show catalogue metadata only; the protected file URL arrives after backend authorization.
export function ContentDetailPage() {
  const { id } = useParams();
  const { user, refreshProfile } = useAuth();
  const { items, loading, error: listError } = usePublicContent();
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [accessUrl, setAccessUrl] = useState('');
  const item = items.find((entry) => String(entry.id) === id);
  const location = useLocation();
  const navigate = useNavigate();
  async function accessContent() {
    if (!user) { navigate('/login', { state: { from: { pathname: location.pathname } } }); return; }
    setBusy('access'); setError(''); setMessage('');
    try { const result = await getContentAccess(id); setAccessUrl(result.content.file_url); }
    catch (failure) { setError(failure.status === 403 ? 'This resource is not in your library yet. Purchase it to unlock access.' : getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(''); }
  }
  async function buyContent() {
    if (!user) { navigate('/login', { state: { from: { pathname: location.pathname } } }); return; }
    setBusy('purchase'); setError(''); setMessage(''); setAccessUrl('');
    try {
      const result = await purchaseContent(id);
      setMessage(`Purchase complete. Your remaining balance is ${result.remaining_credits} credits.`);
      try { await refreshProfile(); } catch { setMessage(`Purchase complete. The displayed balance could not be refreshed; your server balance remains authoritative.`); }
    } catch (failure) { setError(getApiErrorMessage(failure.data, failure.message)); }
    finally { setBusy(''); }
  }
  return <section className="page-shell detail-shell">
    <Link className="back-link" to="/explore">← Back to Explore</Link>
    <LoadState loading={loading} error={listError} empty={item ? '' : 'This resource is unavailable or has been unpublished.'}>
      <article className="detail-card"><div className={`detail-art content-art-${item?.content_type}`} aria-hidden="true"><span>{item?.content_type === 'video' ? '▶' : 'PDF'}</span></div>
        <div className="detail-copy"><div className="content-meta"><span>{item.content_type}</span><span>By {item.creator_username}</span></div><h1>{item.title}</h1><p>{item.description}</p><div className="detail-price"><span>One-time access</span><strong>{item.price} credits</strong></div>
          {error && <p className="notice notice-error" role="alert">{error}</p>}{message && <p className="notice notice-success" role="status">{message}</p>}
          <div className="detail-actions"><button className="button button-primary" onClick={buyContent} disabled={Boolean(busy)}>{busy === 'purchase' ? 'Processing…' : 'Purchase resource'}</button><button className="button button-light" onClick={accessContent} disabled={Boolean(busy)}>{busy === 'access' ? 'Checking access…' : 'Open if already purchased'}</button></div>
          {accessUrl && <a className="button button-secondary" href={accessUrl} target="_blank" rel="noreferrer">Open protected resource ↗</a>}
          <p className="fine-print">Purchases are completed and verified by the {APP_NAME} backend. Your balance is not changed unless the API confirms the purchase.</p>
        </div>
      </article>
    </LoadState>
  </section>;
}
