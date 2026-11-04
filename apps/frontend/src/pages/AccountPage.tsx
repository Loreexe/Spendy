import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type UserStatus } from "../api";
import { useAuth } from "../auth";
import { ImportExportSection } from "../components/ImportExportSection";

const STATUS_LABEL: Record<UserStatus, string> = {
  pending: "In attesa di approvazione",
  active: "Attivo",
  rejected: "Rifiutato",
  disabled: "Disabilitato",
};

export function AccountPage() {
  const { user, setUser, logout } = useAuth();
  const [email, setEmail] = useState(user?.email ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!user) return null;

  async function handleEmail(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      const data = await api.updateEmail(email);
      setUser(data.user);
      setMessage("Email aggiornata.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Aggiornamento non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Account</p>
          <h1>Impostazioni e account</h1>
        </div>
        {!user.is_global_admin && (
          <Link className="button secondary" to="/">
            Torna alla dashboard
          </Link>
        )}
      </section>

      <section className="stack">
        <h2>Profilo e accesso</h2>
        <div className="two-columns">
          <section className="card">
            <h2>Profilo</h2>
            <dl className="facts">
              <div>
                <dt>Identificativo</dt>
                <dd>{user.email ?? user.username}</dd>
              </div>
              <div>
                <dt>Stato</dt>
                <dd>
                  <span className={`badge ${user.status}`}>
                    {STATUS_LABEL[user.status]}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Ruolo</dt>
                <dd>
                  {user.is_global_admin ? "Amministratore globale" : "Utente"}
                </dd>
              </div>
            </dl>
            <p className="muted small">
              {user.is_global_admin
                ? "L'amministratore globale non ha un profilo finanziario."
                : "Un account corrisponde a un profilo personale."}
            </p>
            <button
              type="button"
              className="secondary"
              onClick={() => void logout()}
            >
              Esci
            </button>
          </section>

          <section className="card">
            <h2>Email</h2>
            <p className="muted">
              {user.is_global_admin
                ? "L'email dell'amministratore è opzionale."
                : "L'email è il tuo identificativo di accesso."}
            </p>
            <form onSubmit={handleEmail} className="stack">
              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required={!user.is_global_admin}
                />
              </label>
              {message && <p className="notice success">{message}</p>}
              {error && <p className="error">{error}</p>}
              <button type="submit" disabled={busy}>
                {busy ? "Salvataggio…" : "Salva email"}
              </button>
            </form>
          </section>
        </div>
      </section>

      {!user.is_global_admin && <ImportExportSection />}
    </div>
  );
}
