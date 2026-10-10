import { Link } from 'react-router-dom';

// Reusable 404 surface with a direct route back to the public home page.
export function PlaceholderPage({ title, eyebrow = 'Coming soon', description = 'This feature is not available yet.' }) {
  return <section className="page-shell"><div className="empty-panel"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{description}</p><Link className="button button-primary" to="/">Go to home</Link></div></section>;
}
