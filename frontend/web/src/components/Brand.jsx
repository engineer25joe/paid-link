import { APP_LOGO, APP_NAME } from '../config/brand.js';

export function Brand({ compact = false }) {
  return <span className={`brand-lockup${compact ? ' brand-lockup-compact' : ''}`}>
    <img className="brand-logo" src={APP_LOGO} alt=""/><span className="brand-name">{APP_NAME}</span>
  </span>;
}
