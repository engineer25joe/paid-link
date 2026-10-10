import { PageIntro } from '../components/PageIntro.jsx';

// Purchase records exist in the backend, but there is no learner-owned history endpoint yet.
export function PurchasesPage() {
  return <section className="page-shell"><PageIntro eyebrow="My Purchases" title="Purchase history" description="Review your past learning purchases."/><div className="empty-panel"><span className="empty-icon" aria-hidden="true">◷</span><h2>Purchase history is coming soon</h2><p>The backend currently supports making a purchase, but does not expose a learner purchase-history list.</p></div></section>;
}
