import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

export function RegisterPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Le password non coincidono.");
      return;
    }
    setBusy(true);
    try {
      const result = await api.register(email, password, confirm);
      if (result.pending) {
        navigate("/pending", { replace: true });
      } else {
        navigate("/login", { replace: true, state: { registered: true } });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registrazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <p className="eyebrow">Nuovo account</p>
      <h1>Registrati</h1>
      <p className="muted">
        La registrazione richiede l'approvazione dell'amministratore, salvo
        diversa impostazione.
      </p>
      <form onSubmit={handleSubmit} className="stack">
        <label>
          Email
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <label>
          Conferma password
          <input
            type="password"
            autoComplete="new-password"
            value={confirm}
            onChange={(event) => setConfirm(event.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Invio…" : "Crea account"}
        </button>
      </form>
      <p className="muted small">
        Hai già un account? <Link to="/login">Accedi</Link>
      </p>
    </div>
  );
}
