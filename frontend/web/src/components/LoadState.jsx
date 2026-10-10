// Shared accessible feedback for asynchronous catalogue and workspace requests.
export function LoadState({ loading, error, empty, children }) {
  if (loading) return <p className="notice" role="status">Loading…</p>;
  if (error) return <p className="notice notice-error" role="alert">{error}</p>;
  if (empty) return <p className="notice">{empty}</p>;
  return children;
}
