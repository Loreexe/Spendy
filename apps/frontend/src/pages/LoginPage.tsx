import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { AuthHero } from "../components/AuthHero";
import { InlineMessage } from "../components/InlineMessage";

interface LocationState {
  from?: string;
  registered?: boolean;
}

export function LoginPage() {
  const { user, login, completeTwoFactor } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const state = (location.state ?? {}) as LocationState;

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [challenge, setChallenge] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  function resetChallenge() {
    setChallenge(null);
    setCode("");
    setRecoveryCode(false);
    setError(null);
  }

  async function handlePasswordSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const result = await login(identifier, password);
      if ("two_factor_required" in result && result.two_factor_required) {
        setChallenge(result.challenge);
        setCode("");
        return;
      }
      navigate(state.from ?? "/", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Accesso non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCodeSubmit(event: FormEvent) {
    event.preventDefault();
    if (!challenge) return;
    setError(null);
    setBusy(true);
    try {
      await completeTwoFactor(challenge, code.trim());
      navigate(state.from ?? "/", { replace: true });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Codice non valido o scaduto.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card narrow">
      <AuthHero glow />
      {challenge ? (
        <>
          <h1>Verifica in due passaggi</h1>
          <p className="muted small">
            Inserisci il codice a 6 cifre dell'app di autenticazione
            {recoveryCode ? " oppure un codice di recupero." : "."}
          </p>
          <form onSubmit={handleCodeSubmit} className="stack">
            <label>
              {recoveryCode ? "Codice di recupero" : "Codice di verifica"}
              <input
                type="text"
                inputMode={recoveryCode ? "text" : "numeric"}
                autoComplete="one-time-code"
                autoCapitalize={recoveryCode ? "characters" : "none"}
                value={code}
                onChange={(event) => setCode(event.target.value)}
                required
                autoFocus
              />
            </label>
            {error && <InlineMessage tone="error">{error}</InlineMessage>}
            <button type="submit" disabled={busy || !code.trim()}>
              {busy ? "Verifica…" : "Verifica"}
            </button>
            <button
              type="button"
              className="link-button"
              onClick={() => {
                setRecoveryCode((value) => !value);
                setCode("");
                setError(null);
              }}
              disabled={busy}
            >
              {recoveryCode
                ? "Usa il codice dell'app"
                : "Usa un codice di recupero"}
            </button>
            <button
              type="button"
              className="ghost"
              onClick={resetChallenge}
              disabled={busy}
            >
              Indietro
            </button>
          </form>
        </>
      ) : (
        <>
          <h1>Accedi</h1>
          {state.registered && (
            <InlineMessage tone="success">
              Registrazione completata: ora puoi accedere.
            </InlineMessage>
          )}
          <form onSubmit={handlePasswordSubmit} className="stack">
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
            {error && <InlineMessage tone="error">{error}</InlineMessage>}
            <button type="submit" disabled={busy}>
              {busy ? "Accesso…" : "Accedi"}
            </button>
          </form>
          <p className="muted small">
            Non hai un account? <Link to="/register">Registrati</Link>
          </p>
        </>
      )}
    </div>
  );
}
