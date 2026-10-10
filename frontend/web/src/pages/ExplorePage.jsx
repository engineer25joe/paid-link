import { useMemo, useState } from 'react';
import { ContentCard } from '../components/ContentCard.jsx';
import { LoadState } from '../components/LoadState.jsx';
import { PageIntro } from '../components/PageIntro.jsx';
import { usePublicContent } from '../hooks/usePublicContent.js';

// Search and type filters are client-side because the current catalogue API has no query contract.
export function ExplorePage() {
  const { items, loading, error } = usePublicContent();
  const [search, setSearch] = useState('');
  const [type, setType] = useState('all');
  const visibleItems = useMemo(() => items.filter((item) => {
    const text = `${item.title} ${item.description} ${item.creator_username}`.toLowerCase();
    return text.includes(search.trim().toLowerCase()) && (type === 'all' || item.content_type === type);
  }), [items, search, type]);
  return <section className="page-shell">
    <PageIntro eyebrow="Explore" title="Find your next lesson" description="Search practical learning resources shared by creators."/>
    <div className="catalogue-tools"><label className="search-field"><span aria-hidden="true">⌕</span><span className="visually-hidden">Search learning resources</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by topic, title or creator" type="search"/></label>
      <label className="filter-field"><span className="visually-hidden">Filter content type</span><select value={type} onChange={(event) => setType(event.target.value)}><option value="all">All formats</option><option value="pdf">PDF guides</option><option value="video">Videos</option></select></label>
    </div>
    <LoadState loading={loading} error={error} empty={visibleItems.length ? '' : (items.length ? 'No resources match those filters.' : 'There are no published resources yet.')}>
      <div className="result-caption">{visibleItems.length} {visibleItems.length === 1 ? 'resource' : 'resources'}</div><div className="content-grid">{visibleItems.map((item) => <ContentCard key={item.id} item={item}/>)}</div>
    </LoadState>
  </section>;
}
