import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  api,
  type AuditEvent,
  type McpServiceStatus,
  type Settings,
  type SystemInfo,
  type User,
  type UserStatus,
} from "../api";
import { useAuth } from "../auth";
import { InlineMessage } from "../components/InlineMessage";
import { AdminPageSkeleton } from "../components/PageSkeletons";

const AUDIT_LABEL: Record<string, string> = {
  setup_completed: "Setup completato",
  login_success: "Accesso riuscito",
  login_failed: "Accesso fallito",
  token_login: "Accesso da dispositivo",
  "2fa_verified": "Secondo fattore verificato",
  "2fa_failed": "Secondo fattore fallito",
  "2fa_setup": "Configurazione 2FA avviata",
  "2fa_enabled": "2FA attivata",
  "2fa_disabled": "2FA disattivata",
  "2fa_recovery_codes": "Codici di recupero rigenerati",
  password_changed: "Password cambiata",
  admin_approve: "Account approvato",
  admin_reject: "Account rifiutato",
  admin_settings: "Impostazioni globali modificate",
  device_revoked: "Dispositivo revocato",
  pairing_approved: "Pairing approvato",
  pairing_rejected: "Pairing rifiutato",
  sessions_revoked: "Sessioni revocate",
  session_expired: "Sessione scaduta",
};

const STATUS_LABEL: Record<UserStatus, string> = {
  pending: "In attesa",
  active: "Attivo",
  rejected: "Rifiutato",
  disabled: "Disabilitato",
};

function formatDateTime(value: string | null): string {
  if (!value) return "mai";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("it-IT");
}

export function AdminPage() {
  const { user } = useAuth();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [systemMessage, setSystemMessage] = useState<string | null>(null);
  const [systemMessageError, setSystemMessageError] = useState(false);
  const [busy, setBusy] = useState(false);
  const [checkingUpdates, setCheckingUpdates] = useState(false);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [auditError, setAuditError] = useState<string | null>(null);
  const [auditBusy, setAuditBusy] = useState(false);
  const [mcp, setMcp] = useState<McpServiceStatus | null>(null);
  const [mcpBusy, setMcpBusy] = useState(false);
  const [mcpError, setMcpError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [settingsData, usersData, systemData] = await Promise.all([
        api.adminSettings(),
        api.adminUsers(),
        api.adminSystem(),
      ]);
      setSettings(settingsData);
      setUsers(usersData.users);
      setSystem(systemData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAudit = useCallback(async () => {
    setAuditBusy(true);
    setAuditError(null);
    try {
      const result = await api.adminAudit(50);
      setAudit(result.events);
    } catch (err) {
      setAuditError(
        err instanceof Error ? err.message : "Registro non disponibile.",
      );
    } finally {
      setAuditBusy(false);
    }
  }, []);

  const loadMcp = useCallback(async () => {
    setMcpError(null);
    try {
      setMcp(await api.adminMcpStatus());
    } catch (err) {
      setMcpError(
        err instanceof Error ? err.message : "Stato MCP non disponibile.",
      );
    }
  }, []);

  useEffect(() => {
    void load();
    void loadAudit();
    void loadMcp();
  }, [load, loadAudit, loadMcp]);

  async function toggleMcp() {
    setMcpBusy(true);
    setMcpError(null);
    try {
      setMcp(await api.adminMcpToggle(!(mcp?.enabled ?? false)));
    } catch (err) {
      setMcpError(
        err instanceof Error ? err.message : "Cambio stato non riuscito.",
      );
    } finally {
      setMcpBusy(false);
    }
  }

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

  async function checkUpdates() {
    setCheckingUpdates(true);
    setSystemMessage(null);
    setSystemMessageError(false);
    try {
      const updated = await api.adminSystem(true);
      setSystem(updated);
      if (updated.error) {
        setSystemMessageError(true);
        setSystemMessage(updated.error);
      } else if (updated.update_available && updated.latest) {
        setSystemMessage(
          `Nuova versione disponibile: ${updated.latest.version}.`,
        );
      } else {
        setSystemMessage("Nessun aggiornamento disponibile.");
      }
    } catch (err) {
      setSystemMessageError(true);
      setSystemMessage(
        err instanceof Error ? err.message : "Controllo non riuscito.",
      );
    } finally {
      setCheckingUpdates(false);
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

  if (loading) return <AdminPageSkeleton />;

  const pending = users.filter((user) => user.status === "pending");

  return (
    <div className="stack-page">
      {user && !user.totp_enabled && (
        <InlineMessage tone="warning">
          La verifica a due fattori non è attiva.{" "}
          <Link to="/settings">Attivala nelle impostazioni</Link> prima di
          esporre il servizio su Internet.
        </InlineMessage>
      )}
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
        <p className="eyebrow">MCP</p>
        <h2>Servizio MCP</h2>
        {mcpError && <InlineMessage tone="error">{mcpError}</InlineMessage>}
        {mcp ? (
          <div className="stack">
            <p>
              Stato:{" "}
              <strong>{mcp.enabled ? "acceso" : "spento"}</strong> · token
              attivi: <strong>{mcp.active_tokens}</strong>
            </p>
            <p className="muted small">
              L’interruttore scrive il flag letto dall’unità host-side; il
              container viene avviato o fermato entro circa un minuto.
            </p>
            <div className="actions">
              <button
                type="button"
                className={mcp.enabled ? "danger" : undefined}
                onClick={() => void toggleMcp()}
                disabled={mcpBusy}
              >
                {mcpBusy
                  ? "Aggiorno…"
                  : mcp.enabled
                    ? "Spegni servizio MCP"
                    : "Accendi servizio MCP"}
              </button>
            </div>
          </div>
        ) : (
          <p className="muted">Stato MCP non disponibile.</p>
        )}
      </section>

      <section className="card">
        <p className="eyebrow">Sistema</p>
        <h2>Informazioni e aggiornamenti</h2>
        {system ? (
          <div className="stack">
            <div className="system-grid">
              <div>
                <span className="muted small">Versione backend</span>
                <strong>{system.current_version}</strong>
              </div>
              <div>
                <span className="muted small">Versione frontend</span>
                <strong>{__APP_VERSION__}</strong>
              </div>
              <div>
                <span className="muted small">Database</span>
                <strong>
                  {system.database === "ok"
                    ? "Raggiungibile"
                    : "Non raggiungibile"}
                </strong>
              </div>
              <div>
                <span className="muted small">Ultimo controllo</span>
                <strong>{formatDateTime(system.checked_at)}</strong>
              </div>
            </div>

            {system.current_version !== __APP_VERSION__ && (
              <p className="error">
                Le versioni di backend e frontend non coincidono. Ricarica la
                pagina o verifica il deployment.
              </p>
            )}

            <div className="system-block">
              <span className="muted small">Backup globale</span>
              {system.backup ? (
                <div className="stack">
                  <p>
                    Ultimo tentativo:{" "}
                    <strong>{formatDateTime(system.backup.last_run ?? null)}</strong>
                    {" · "}
                    Esito:{" "}
                    <strong>
                      {system.backup.status === "ok"
                        ? "riuscito"
                        : system.backup.status === "failed"
                          ? "fallito"
                          : system.backup.status ?? "sconosciuto"}
                    </strong>
                  </p>
                  <p className="muted small">
                    Ultimo successo:{" "}
                    {formatDateTime(system.backup.last_success ?? null)}
                    {" · "}
                    Offsite: {system.backup.offsite ?? "non eseguito"}
                  </p>
                  {system.backup.restore_test && (
                    <p className="muted small">
                      Test di ripristino:{" "}
                      {system.backup.restore_test.status ?? "sconosciuto"}{" "}
                      ({formatDateTime(
                        system.backup.restore_test.last_run ?? null,
                      )})
                    </p>
                  )}
                  {system.backup.last_error && (
                    <p className="error">{system.backup.last_error}</p>
                  )}
                </div>
              ) : (
                <p className="muted small">
                  Nessuno stato disponibile: monta il file prodotto dal job di
                  backup.
                </p>
              )}
            </div>

            <div className="actions">
              <button
                type="button"
                onClick={() => void checkUpdates()}
                disabled={checkingUpdates}
              >
                {checkingUpdates
                  ? "Controllo in corso..."
                  : "Controlla aggiornamenti"}
              </button>
            </div>

            {systemMessage && (
              <p className={systemMessageError ? "error" : "notice success"}>
                {systemMessage}
              </p>
            )}

            {system.latest && (
              <div className="stack">
                <p className="muted small">
                  Ultima release stabile:{" "}
                  <strong>{system.latest.version}</strong>
                  {system.latest.published_at
                    ? ` · ${formatDateTime(system.latest.published_at)}`
                    : ""}
                </p>
                <p>
                  <a
                    href={system.latest.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Note di rilascio
                  </a>
                </p>
                {system.latest.notes && (
                  <details>
                    <summary>Note della release</summary>
                    <pre className="release-notes">{system.latest.notes}</pre>
                  </details>
                )}
              </div>
            )}

            <p className="muted small">
              Disco, stato dei container e ultimo backup saranno disponibili con
              l'agente host della Tappa 2.
            </p>
          </div>
        ) : (
          <p className="muted">Informazioni di sistema non disponibili.</p>
        )}
      </section>

      <section className="card">
        <div className="section-heading">
          <h2>Registro attività</h2>
          <button
            type="button"
            className="secondary small-button"
            onClick={() => void loadAudit()}
            disabled={auditBusy}
          >
            {auditBusy ? "Aggiorno…" : "Aggiorna"}
          </button>
        </div>
        {auditError && <InlineMessage tone="error">{auditError}</InlineMessage>}
        {audit.length === 0 ? (
          <p className="muted">Nessun evento registrato.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Azione</th>
                  <th>Attore</th>
                  <th>Dettaglio</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((event) => (
                  <tr key={event.id}>
                    <td>{formatDateTime(event.created_at)}</td>
                    <td>{AUDIT_LABEL[event.action] ?? event.action}</td>
                    <td>{event.actor_label || "—"}</td>
                    <td>{event.target || "—"}</td>
                    <td>{event.ip || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
