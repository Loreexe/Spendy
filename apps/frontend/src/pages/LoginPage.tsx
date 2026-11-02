import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

interface LocationState {
  from?: string;
  registered?: boolean;
}

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(identifier, password);
      navigate(state.from ?? "/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Accesso non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <p className="eyebrow">Spendy</p>
      <h1>Accedi</h1>
      {state.registered && (
        <p className="notice success">Registrazione completata: ora puoi accedere.</p>
      )}
      <form onSubmit={handleSubmit} className="stack">
        <label>
          Email o username
          <input
            type="text"
            autoComplete="username"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            required
            autoFocus
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button type="submit" disabled={busy}>
          {busy ? "Accesso…" : "Accedi"}
        </button>
      </form>
      <p className="muted small">
        Non hai un account? <Link to="/register">Registrati</Link>
      </p>
    </div>
  );
}
