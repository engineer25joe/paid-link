import { APP_NAME } from '../config/brand.js';

// Text wordmark placeholder; replace this component when the final logo is approved.
export function Brand({ compact = false }) {
  return <span className={`brand-lockup${compact ? ' brand-lockup-compact' : ''}`} aria-label={APP_NAME}>
    <span className="brand-name">{APP_NAME}</span><span className="brand-accent" aria-hidden="true">.</span>
  </span>;
}
