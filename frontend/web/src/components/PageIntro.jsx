// Standard page heading keeps marketplace and workspace hierarchy consistent.
export function PageIntro({ eyebrow, title, description, action }) {
  return <header className="page-intro"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{description && <p className="page-description">{description}</p>}</div>{action}</header>;
}
