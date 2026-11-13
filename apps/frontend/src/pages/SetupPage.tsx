import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type SetupStatus } from "../api";
import { useAuth } from "../auth";
import { AuthHero } from "../components/AuthHero";
import { AuthPageSkeleton } from "../components/PageSkeletons";

export function SetupPage() {
  const { refresh } = useAuth();
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .setupStatus()
      .then(setStatus)
      .catch(() => setError("Impossibile contattare il backend."));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("La password deve contenere almeno 8 caratteri.");
      return;
    }
    if (password !== confirm) {
      setError("Le password non coincidono.");
      return;
    }
    setBusy(true);
    try {
      await api.setup(password, confirm);
      await refresh();
      // Ricarica completa: il gate di setup rilegge lo stato aggiornato.
      window.location.assign("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  if (!status) {
    return error ? <ErrorCard message={error} /> : <AuthPageSkeleton />;
  }

  if (!status.setup_required) {
    return (
      <div className="card narrow">
        <h1>Setup già completato</h1>
        <p className="muted">
          La password dell'amministratore è già stata impostata.
        </p>
        <Link className="button" to="/login">
          Vai al login
        </Link>
      </div>
    );
  }

  if (!status.can_setup) {
    return (
      <div className="card narrow">
        <h1>Setup non disponibile</h1>
        <p>
          Il primo accesso dell'amministratore si può configurare solo da{" "}
          <strong>localhost</strong> o dalla rete <strong>Tailscale</strong>.
        </p>
        <p className="muted">
          Apri Spendy dall'indirizzo privato e ricarica questa pagina.
        </p>
      </div>
    );
  }

  return (
    <div className="card narrow">
      <AuthHero />
      <h1>Imposta la password di admin</h1>
      <p className="muted">
        L&apos;account globale <code>admin</code> non ha ancora una password.
      </p>
      <form onSubmit={handleSubmit} className="stack">
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
          {busy ? "Impostazione…" : "Imposta password"}
        </button>
      </form>
    </div>
  );
}

function ErrorCard({ message }: { message: string }) {
  return (
    <div className="card narrow">
      <h1>Errore</h1>
      <p className="error">{message}</p>
    </div>
  );
}
