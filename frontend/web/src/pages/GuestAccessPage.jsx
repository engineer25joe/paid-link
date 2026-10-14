import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getGuestContent } from '../api/marketplace.js';
import { getApiErrorMessage } from '../api/errors.js';
import { useCountdown } from '../hooks/useCountdown.js';

export function GuestAccessPage() {
  const { token } = useParams(); const [resource, setResource] = useState(null); const [error, setError] = useState('');
  const countdown = useCountdown(resource?.expires_at || 0);
  useEffect(() => { let active = true; getGuestContent(token).then((data) => { if (active) setResource(data); }).catch((failure) => { if (active) setError(getApiErrorMessage(failure.data, failure.message)); }); return () => { active = false; }; }, [token]);
  if (error || (resource && countdown.expired)) return <section className="page-shell narrow-shell"><div className="notice notice-error" role="alert"><h1>Guest access expired or unavailable</h1><p>{resource && countdown.expired ? 'This temporary access link has expired.' : error}</p><Link className="button button-light" to="/explore">Explore ElimuBang</Link></div></section>;
  if (!resource) return <section className="page-shell narrow-shell"><p className="notice" role="status">Verifying temporary access…</p></section>;
  return <section className="page-shell"><div className="share-expiry"><span>Access expires in</span><strong>{countdown.label}</strong></div><article className="detail-card"><div className="detail-copy"><h1>{resource.content.title}</h1><p>{resource.content.description}</p><div className="protected-viewer">{resource.content.content_type === 'pdf' ? <><iframe title={`PDF: ${resource.content.title}`} src={resource.content.file_url} className="pdf-viewer"/><a className="button button-primary" href={resource.content.file_url} target="_blank" rel="noopener noreferrer">Download PDF</a></> : <video className="video-viewer" controls playsInline preload="metadata" src={resource.content.file_url}/>}</div></div></article><p className="fine-print">This temporary link is private. Access is checked by ElimuBang and is revoked when the timer expires.</p></section>;
}
