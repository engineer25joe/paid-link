import { PageIntro } from '../components/PageIntro.jsx';

// A transparent empty state: no learner purchase-list endpoint currently exists.
export function LibraryPage() {
  return <section className="page-shell"><PageIntro eyebrow="My Library" title="Your learning collection" description="Purchased resources will be gathered here."/><div className="empty-panel"><span className="empty-icon" aria-hidden="true">▤</span><h2>Your library is ready when you are</h2><p>The current API can verify access to a resource you own, but does not yet return a list of your purchased resources.</p></div></section>;
}
