import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type UserStatus } from "../api";
import { useAuth } from "../auth";

const STATUS_LABEL: Record<UserStatus, string> = {
  pending: "In attesa di approvazione",
  active: "Attivo",
  rejected: "Rifiutato",
  disabled: "Disabilitato",
};

export function HomePage() {
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
    <div className="grid">
      <section className="card">
        <p className="eyebrow">Account</p>
        <h1>Ciao{user.username ? `, ${user.username}` : ""}</h1>
        <dl className="facts">
          <div>
            <dt>Identificativo</dt>
            <dd>{user.email ?? user.username}</dd>
          </div>
          <div>
            <dt>Stato</dt>
            <dd>
              <span className={`badge ${user.status}`}>{STATUS_LABEL[user.status]}</span>
            </dd>
          </div>
          <div>
            <dt>Ruolo</dt>
            <dd>{user.is_global_admin ? "Amministratore globale" : "Utente"}</dd>
          </div>
        </dl>
        {user.is_global_admin && (
          <p className="muted">
            L'amministratore globale gestisce impostazioni e account e non ha un
            profilo finanziario.
          </p>
        )}
        <button type="button" className="secondary" onClick={() => void logout()}>
          Esci
        </button>
      </section>

      <section className="card">
        <p className="eyebrow">Impostazioni</p>
        <h2>Email dell'account</h2>
        <p className="muted">
          {user.is_global_admin
            ? "L'email dell'amministratore è opzionale e serve per il recupero futuro."
            : "L'email è il tuo identificativo di accesso."}
        </p>
        <form onSubmit={handleEmail} className="stack">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder={
                user.is_global_admin ? "admin@example.com (opzionale)" : "nome@example.com"
              }
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

      <section className="card">
        <p className="eyebrow">Prossimamente</p>
        <h2>Funzionalità finanziarie</h2>
        <p className="muted">
          Conti, movimenti, salvadanai, gruppi e investimenti non fanno parte di
          questo primo traguardo. Le fondamenta tecniche sono pronte per
          accoglierli.
        </p>
        {user.is_global_admin && (
          <Link className="button secondary" to="/admin">
            Gestisci gli account
          </Link>
        )}
      </section>
    </div>
  );
}
