import { Link } from "react-router-dom";
import { AuthHero } from "../components/AuthHero";

export function PendingPage() {
  return (
    <div className="card narrow">
      <AuthHero />
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
