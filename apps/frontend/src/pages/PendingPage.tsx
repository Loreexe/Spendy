import { Link } from "react-router-dom";

export function PendingPage() {
  return (
    <div className="card narrow">
      <p className="eyebrow">Registrazione inviata</p>
      <h1>Account in attesa</h1>
      <p>
        Il tuo account è stato creato ma è <strong>in attesa di approvazione</strong>.
        Potrai accedere quando l'amministratore lo avrà approvato.
      </p>
      <Link className="button" to="/login">
        Torna al login
      </Link>
    </div>
  );
}
