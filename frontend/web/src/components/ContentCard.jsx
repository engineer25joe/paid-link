import { Link } from 'react-router-dom';

// Public catalogue cards contain metadata only, never protected file URLs.
export function ContentCard({ item, manage = false }) {
  const destination = manage ? `/creator/content/${item.id}/edit` : `/content/${item.id}`;
  const action = manage ? 'Edit details' : 'View details';
  return <article className="content-card">
    <div className={`content-art content-art-${item.content_type}`} aria-hidden="true"><span>{item.content_type === 'video' ? '▶' : 'PDF'}</span></div>
    <div className="content-card-body"><div className="content-meta"><span>{item.content_type}</span><span>{item.creator_username}</span></div>
      <h3><Link to={destination}>{item.title}</Link></h3><p>{item.description}</p>
      <div className="content-card-foot"><strong>KES {item.price_kes} · {item.price} credits</strong><Link className="arrow-link" to={destination} aria-label={`${action}: ${item.title}`}>{action} ↗</Link></div>
    </div>
  </article>;
}
