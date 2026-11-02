import { useCallback, useEffect, useState } from "react";
import { api, type Settings, type User, type UserStatus } from "../api";
import { LoadingScreen } from "../components/Guards";

const STATUS_LABEL: Record<UserStatus, string> = {
  pending: "In attesa",
  active: "Attivo",
  rejected: "Rifiutato",
  disabled: "Disabilitato",
};

export function AdminPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [settingsData, usersData] = await Promise.all([
        api.adminSettings(),
        api.adminUsers(),
      ]);
      setSettings(settingsData);
      setUsers(usersData.users);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function changeMode(mode: "approval" | "open") {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateSettings(mode);
      setSettings(updated);
      setMessage(
        mode === "approval"
          ? "Registrazione con approvazione attiva."
          : "Registrazione aperta attiva.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Salvataggio non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function decide(user: User, decision: "approve" | "reject") {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.adminDecision(user.id, decision);
      setMessage(
        decision === "approve"
          ? `Account ${user.email ?? user.username} approvato.`
          : `Account ${user.email ?? user.username} rifiutato.`,
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingScreen />;

  const pending = users.filter((user) => user.status === "pending");

  return (
    <div className="stack-page">
      <section className="card">
        <p className="eyebrow">Amministrazione</p>
        <h1>Impostazioni globali</h1>
        {settings && (
          <div className="stack">
            <p className="muted">
              Stato del setup:{" "}
              <strong>{settings.setup_completed ? "completato" : "da completare"}</strong>
            </p>
            <fieldset className="radio-group">
              <legend>Politica di registrazione</legend>
              <label>
                <input
                  type="radio"
                  name="registration-mode"
                  checked={settings.registration_mode === "approval"}
                  onChange={() => void changeMode("approval")}
                  disabled={busy}
                />
                Con approvazione dell'amministratore
              </label>
              <label>
                <input
                  type="radio"
                  name="registration-mode"
                  checked={settings.registration_mode === "open"}
                  onChange={() => void changeMode("open")}
                  disabled={busy}
                />
                Aperta (accesso immediato)
              </label>
            </fieldset>
          </div>
        )}
        {message && <p className="notice success">{message}</p>}
        {error && <p className="error">{error}</p>}
      </section>

      <section className="card">
        <h2>Richieste in attesa ({pending.length})</h2>
        {pending.length === 0 ? (
          <p className="muted">Nessuna richiesta in attesa.</p>
        ) : (
          <ul className="user-list">
            {pending.map((user) => (
              <li key={user.id}>
                <div>
                  <strong>{user.email ?? user.username}</strong>
                  <span className="muted small">
                    {" "}
                    · registrato il{" "}
                    {new Date(user.date_joined).toLocaleDateString("it-IT")}
                  </span>
                </div>
                <div className="actions">
                  <button
                    type="button"
                    onClick={() => void decide(user, "approve")}
                    disabled={busy}
                  >
                    Approva
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => void decide(user, "reject")}
                    disabled={busy}
                  >
                    Rifiuta
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2>Tutti gli account ({users.length})</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Identificativo</th>
                <th>Ruolo</th>
                <th>Stato</th>
                <th>Registrato</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td>{user.email ?? user.username}</td>
                  <td>{user.is_global_admin ? "Admin globale" : "Utente"}</td>
                  <td>
                    <span className={`badge ${user.status}`}>
                      {STATUS_LABEL[user.status]}
                    </span>
                  </td>
                  <td>{new Date(user.date_joined).toLocaleDateString("it-IT")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
