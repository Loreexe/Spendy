import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="card narrow">
      <p className="eyebrow">404</p>
      <h1>Pagina non trovata</h1>
      <Link className="button" to="/">
        Torna alla home
      </Link>
    </div>
  );
}
