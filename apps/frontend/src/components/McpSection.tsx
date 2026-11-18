import { useCallback, useEffect, useState } from "react";
import { Check, Copy, KeyRound, Plug, ShieldCheck, Trash2 } from "lucide-react";
import {
  api,
  type McpArea,
  type McpToken,
} from "../api";
import { InlineMessage } from "./InlineMessage";
import { SkeletonLines } from "./SkeletonLines";

function matches(query: string, keywords: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return keywords.toLowerCase().includes(needle);
}

function formatMoment(value: string | null): string {
  if (!value) return "mai";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type Permissions = Record<string, "read" | "write">;

export function McpSection({ query }: { query: string }) {
  const [areas, setAreas] = useState<McpArea[]>([]);
  const [tokens, setTokens] = useState<McpToken[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [password, setPassword] = useState("");
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [selected, setSelected] = useState<McpToken | null>(null);
  const [draft, setDraft] = useState<Permissions>({});
  const [permissionPassword, setPermissionPassword] = useState("");
  const [revokePassword, setRevokePassword] = useState("");
  const [revoking, setRevoking] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [catalog, tokenResult] = await Promise.all([
        api.mcpCatalog(),
        api.mcpTokens(),
      ]);
      setAreas(catalog.areas);
      setTokens(tokenResult.tokens);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Configurazione MCP non disponibile.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function createToken() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.createMcpToken(newName.trim(), password);
      setCreatedToken(result.token);
      setShowCreate(false);
      setNewName("");
      setPassword("");
      setMessage("Token creato: copialo ora, non verrà mostrato di nuovo.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  function selectToken(token: McpToken) {
    setSelected(token);
    setDraft({ ...token.permissions });
    setPermissionPassword("");
    setRevokePassword("");
    setRevoking(false);
    setError(null);
    setMessage(null);
  }

  function toggle(operationId: string, kind: "read" | "write") {
    setDraft((current) => {
      const next = { ...current };
      if (next[operationId]) {
        delete next[operationId];
      } else {
        next[operationId] = kind;
      }
      return next;
    });
  }

  async function savePermissions() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const updated = await api.updateMcpPermissions(
        selected.id,
        permissionPassword,
        draft,
      );
      setTokens((current) =>
        current.map((token) => (token.id === updated.id ? updated : token)),
      );
      setSelected(updated);
      setPermissionPassword("");
      setMessage("Permessi aggiornati.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Salvataggio non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function revokeToken() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api.revokeMcpToken(selected.id, revokePassword);
      setSelected(null);
      setRevoking(false);
      setRevokePassword("");
      setMessage("Token revocato.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revoca non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function copyToken() {
    if (!createdToken) return;
    try {
      await navigator.clipboard.writeText(createdToken);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copia non disponibile: seleziona il token manualmente.");
    }
  }

  if (!matches(query, "mcp token client claude hermes permessi operazioni lettura scrittura")) {
    return null;
  }

  return (
    <section className="profile-section">
      <div className="section-heading">
        <h2>MCP</h2>
        <Plug size={18} aria-hidden="true" />
      </div>
      <p className="muted small">
        Collega un client MCP (Claude Code, Hermes, …) con un token dedicato.
        Ogni token ha permessi separati per singola operazione; tutto è
        disattivato finché non lo abiliti.
      </p>

      {loading ? (
        <SkeletonLines rows={2} label="Caricamento MCP" />
      ) : (
        <>
          {error && <InlineMessage tone="error">{error}</InlineMessage>}
          {message && <InlineMessage tone="success">{message}</InlineMessage>}

          {createdToken && (
            <div className="pairing-box">
              <div className="pairing-details">
                <strong>Token appena creato</strong>
                <p className="muted small">
                  Copialo nel client MCP. Non verrà mostrato di nuovo.
                </p>
                <code className="pairing-code">{createdToken}</code>
                <div className="pairing-actions">
                  <button
                    type="button"
                    className="secondary small-button"
                    onClick={() => void copyToken()}
                  >
                    {copied ? (
                      <Check size={14} aria-hidden="true" />
                    ) : (
                      <Copy size={14} aria-hidden="true" />
                    )}
                    {copied ? "Copiato" : "Copia token"}
                  </button>
                  <button
                    type="button"
                    className="ghost small-button"
                    onClick={() => setCreatedToken(null)}
                  >
                    Chiudi
                  </button>
                </div>
              </div>
            </div>
          )}

          <div className="pairing-actions">
            <button
              type="button"
              onClick={() => {
                setShowCreate((value) => !value);
                setError(null);
              }}
              disabled={busy}
            >
              <KeyRound size={16} aria-hidden="true" /> Nuovo token
            </button>
          </div>

          {showCreate && (
            <div className="stack">
              <label>
                Nome del client
                <input
                  value={newName}
                  onChange={(event) => setNewName(event.target.value)}
                  placeholder="Claude Code, Hermes…"
                  maxLength={100}
                />
              </label>
              <label>
                Password attuale
                <input
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
              </label>
              <div className="pairing-actions">
                <button
                  type="button"
                  onClick={() => void createToken()}
                  disabled={busy || !newName.trim() || !password}
                >
                  Crea token
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => setShowCreate(false)}
                  disabled={busy}
                >
                  Annulla
                </button>
              </div>
            </div>
          )}

          {tokens.length === 0 ? (
            <p className="muted small">Nessun token MCP configurato.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Client</th>
                    <th>Token</th>
                    <th>Ultimo uso</th>
                    <th>Operazioni</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {tokens.map((token) => (
                    <tr key={token.id}>
                      <td>
                        {token.name}
                        {token.revoked_at && (
                          <span className="badge disabled"> revocato</span>
                        )}
                      </td>
                      <td>{token.prefix}…</td>
                      <td>{formatMoment(token.last_used_at)}</td>
                      <td>{Object.keys(token.permissions).length}</td>
                      <td>
                        <button
                          type="button"
                          className="secondary small-button"
                          onClick={() => selectToken(token)}
                          disabled={busy || Boolean(token.revoked_at)}
                        >
                          Gestisci
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {selected && (
            <div className="stack">
              <div className="section-heading">
                <h2>{selected.name}</h2>
                <ShieldCheck size={16} aria-hidden="true" />
              </div>
              {areas.map((area) => (
                <div key={area.area}>
                  <strong>{area.area}</strong>
                  <div className="stack">
                    {area.operations.map((operation) => (
                      <label key={operation.id}>
                        <input
                          type="checkbox"
                          checked={Boolean(draft[operation.id])}
                          onChange={() =>
                            toggle(operation.id, operation.kind)
                          }
                          disabled={busy}
                        />
                        {operation.label}{" "}
                        <span className="muted small">
                          ({operation.kind === "read" ? "lettura" : "scrittura"})
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
              <label>
                Password attuale per salvare i permessi
                <input
                  type="password"
                  autoComplete="current-password"
                  value={permissionPassword}
                  onChange={(event) => setPermissionPassword(event.target.value)}
                />
              </label>
              <div className="pairing-actions">
                <button
                  type="button"
                  onClick={() => void savePermissions()}
                  disabled={busy || !permissionPassword}
                >
                  Salva permessi
                </button>
                <button
                  type="button"
                  className="ghost"
                  onClick={() => setSelected(null)}
                  disabled={busy}
                >
                  Chiudi
                </button>
              </div>

              {!revoking ? (
                <div className="pairing-actions">
                  <button
                    type="button"
                    className="danger small-button"
                    onClick={() => setRevoking(true)}
                    disabled={busy}
                  >
                    <Trash2 size={14} aria-hidden="true" /> Revoca token
                  </button>
                </div>
              ) : (
                <div className="stack">
                  <p className="muted small">
                    La revoca è immediata: il client non potrà più accedere.
                  </p>
                  <label>
                    Password attuale
                    <input
                      type="password"
                      autoComplete="current-password"
                      value={revokePassword}
                      onChange={(event) => setRevokePassword(event.target.value)}
                    />
                  </label>
                  <div className="pairing-actions">
                    <button
                      type="button"
                      className="danger"
                      onClick={() => void revokeToken()}
                      disabled={busy || !revokePassword}
                    >
                      {busy ? "Revoco…" : "Conferma revoca"}
                    </button>
                    <button
                      type="button"
                      className="ghost"
                      onClick={() => setRevoking(false)}
                      disabled={busy}
                    >
                      Annulla
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </section>
  );
}
