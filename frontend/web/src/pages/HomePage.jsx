import { Link } from 'react-router-dom';
import { APP_NAME } from '../config/brand.js';
import { ContentCard } from '../components/ContentCard.jsx';
import { LoadState } from '../components/LoadState.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import { usePublicContent } from '../hooks/usePublicContent.js';

// Shared signed-in and public marketplace landing page.
export function HomePage() {
  const { user, viewMode } = useAuth();
  const { items, loading, error } = usePublicContent();
  const canManageContent = user?.role === 'creator' || (user?.role === 'admin' && viewMode === 'creator');
  return <div className="home-page">
    <section className="home-hero"><div className="home-hero-copy">
      <p className="eyebrow"><span className="brand-pip"/> Learn something useful today</p>
      <h1>Good ideas.<br/><span>Better learning.</span></h1>
      <p className="home-lede">Practical resources from people who care about what they teach. Find your next lesson and learn at your own pace.</p>
      <div className="hero-actions"><Link className="button button-primary" to="/explore">Explore the library <span aria-hidden="true">↗</span></Link>{!user && <Link className="button button-light" to="/register">Create an account</Link>}</div>
      {user && <p className="credit-chip">Available balance <strong>{user.credits ?? '—'} credits</strong></p>}
    </div><div className="hero-visual" aria-label={`${APP_NAME} learning resources`}><div className="hero-shape hero-shape-purple"/><div className="hero-shape hero-shape-red"/><div className="hero-note"><span className="note-icon">✦</span><div><strong>Learn your way</strong><small>Short lessons. Useful skills.</small></div></div><div className="hero-stats"><strong>{items.length.toString().padStart(2, '0')}</strong><span>resources<br/>to explore</span></div></div></section>
    <section className="section-block"><div className="section-heading"><div><p className="eyebrow">Handpicked for curious minds</p><h2>Explore what’s new</h2></div><Link className="arrow-link" to="/explore">See all resources <span aria-hidden="true">→</span></Link></div>
      <LoadState loading={loading} error={error} empty={items.length ? '' : 'New learning resources are on their way.'}><div className="content-grid">{items.slice(0, 3).map((item) => <ContentCard key={item.id} item={item}/>)}</div></LoadState>
    </section>
    <section className="creator-callout"><div><p className="eyebrow">For people who teach</p><h2>Turn what you know<br/>into someone’s next skill.</h2>{!canManageContent && <p className="creator-note">Creator access is managed by the platform.</p>}</div><Link className="button button-outline" to={canManageContent ? '/creator/content' : '/explore'}>{canManageContent ? 'Manage your content' : 'Keep exploring'} <span aria-hidden="true">↗</span></Link></section>
  </div>;
}
