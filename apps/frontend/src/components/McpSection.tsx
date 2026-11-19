import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bell,
  Check,
  Clock,
  Copy,
  KeyRound,
  LayoutDashboard,
  PiggyBank,
  Plug,
  ReceiptText,
  Search,
  ShieldCheck,
  Tags,
  Trash2,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { api, type McpArea, type McpToken } from "../api";
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

async function writeClipboard(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    // Clipboard API richiede HTTPS/localhost: fallback per l'accesso LAN in HTTP.
    try {
      const area = document.createElement("textarea");
      area.value = value;
      area.setAttribute("readonly", "");
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      const copied = document.execCommand("copy");
      area.remove();
      return copied;
    } catch {
      return false;
    }
  }
}

const AREA_ICONS: Record<string, typeof Wallet> = {
  Conti: Wallet,
  Movimenti: ReceiptText,
  Cestino: Trash2,
  "Categorie e tag": Tags,
  Salvadanai: PiggyBank,
  Investimenti: TrendingUp,
  Automazioni: Clock,
  Notifiche: Bell,
  "Dashboard e ricerca": LayoutDashboard,
  "Import/Export": Plug,
  Profilo: Plug,
};

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
  const [copiedToken, setCopiedToken] = useState(false);
  const [copiedHeader, setCopiedHeader] = useState(false);
  const [copiedEndpoint, setCopiedEndpoint] = useState(false);

  const [selected, setSelected] = useState<McpToken | null>(null);
  const [draft, setDraft] = useState<Permissions>({});
  const [permissionQuery, setPermissionQuery] = useState("");
  const [permissionPassword, setPermissionPassword] = useState("");
  const [revokePassword, setRevokePassword] = useState("");
  const [revoking, setRevoking] = useState(false);
  const [busy, setBusy] = useState(false);

  const endpoint = `${window.location.origin}/mcp`;

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

  const visibleAreas = useMemo(() => {
    const needle = permissionQuery.trim().toLowerCase();
    return areas
      .map((area) => ({
        ...area,
        operations: needle
          ? area.operations.filter(
              (operation) =>
                operation.label.toLowerCase().includes(needle) ||
                operation.id.toLowerCase().includes(needle),
            )
          : area.operations,
      }))
      .filter((area) => area.operations.length > 0);
  }, [areas, permissionQuery]);

  const totalOperations = areas.reduce(
    (total, area) => total + area.operations.length,
    0,
  );

  async function copy(
    value: string,
    target: "token" | "header" | "endpoint",
  ) {
    if (!(await writeClipboard(value))) {
      setError("Copia non disponibile: seleziona il testo manualmente.");
      return;
    }
    if (target === "token") {
      setCopiedToken(true);
      window.setTimeout(() => setCopiedToken(false), 2000);
    } else if (target === "header") {
      setCopiedHeader(true);
      window.setTimeout(() => setCopiedHeader(false), 2000);
    } else {
      setCopiedEndpoint(true);
      window.setTimeout(() => setCopiedEndpoint(false), 2000);
    }
  }

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
    setPermissionQuery("");
    setPermissionPassword("");
    setRevokePassword("");
    setRevoking(false);
    setError(null);
    setMessage(null);
  }

  function setLevel(operationId: string, kind: "read" | "write" | "off") {
    setDraft((current) => {
      const next = { ...current };
      if (kind === "off") {
        delete next[operationId];
      } else {
        next[operationId] = kind;
      }
      return next;
    });
  }

  function enableReads(area: McpArea) {
    setDraft((current) => {
      const next = { ...current };
      for (const operation of area.operations) {
        if (operation.kind === "read") next[operation.id] = "read";
      }
      return next;
    });
  }

  function disableArea(area: McpArea) {
    setDraft((current) => {
      const next = { ...current };
      for (const operation of area.operations) delete next[operation.id];
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

  if (!matches(query, "mcp endpoint token client claude hermes permessi operazioni lettura scrittura")) {
    return null;
  }

  return (
    <section className="profile-section">
      <div className="section-heading">
        <h2>MCP</h2>
        <Plug size={18} aria-hidden="true" />
      </div>
      <p className="muted small">
        Collega Claude Code, Hermes o un altro client MCP. Ogni client ha un
        token dedicato e permessi separati per ogni operazione.
      </p>

      {loading ? (
        <SkeletonLines rows={3} label="Caricamento MCP" />
      ) : (
        <>
          {error && <InlineMessage tone="error">{error}</InlineMessage>}
          {message && <InlineMessage tone="success">{message}</InlineMessage>}

          <div className="mcp-guide">
            <div className="mcp-guide-head">
              <div>
                <h3>Come collegare un client</h3>
                <p className="muted small">
                  Nel client scegli <strong>Streamable HTTP</strong>, incolla
                  l’URL e usa il token come <strong>Bearer token</strong>.
                </p>
              </div>
              <ShieldCheck size={22} aria-hidden="true" />
            </div>
            <div className="mcp-endpoint-grid">
              <div className="mcp-endpoint-item">
                <span className="muted small">Endpoint</span>
                <code>{endpoint}</code>
                <button
                  type="button"
                  className="secondary small-button"
                  onClick={() => void copy(endpoint, "endpoint")}
                >
                  {copiedEndpoint ? (
                    <Check size={14} aria-hidden="true" />
                  ) : (
                    <Copy size={14} aria-hidden="true" />
                  )}
                  {copiedEndpoint ? "Copiato" : "Copia URL"}
                </button>
              </div>
              <div className="mcp-endpoint-item">
                <span className="muted small">Autenticazione</span>
                <code>Authorization: Bearer &lt;token&gt;</code>
                <span className="muted small">
                  Il token generato include già il prefisso <code>mcp_</code>:
                  incollalo interamente dopo Bearer.
                </span>
              </div>
            </div>
            <InlineMessage tone="warning">
              Non usare un token di <strong>Dispositivi</strong>: non funziona
              per MCP. Crea un token qui sotto, in <strong>Impostazioni → MCP</strong>.
            </InlineMessage>
          </div>

          {createdToken && (
            <div className="mcp-token-reveal">
              <strong>Token appena creato</strong>
              <p className="muted small">
                Copialo nel client: non verrà mostrato di nuovo.
              </p>
              <code>{createdToken}</code>
              <div className="pairing-actions">
                <button
                  type="button"
                  className="secondary small-button"
                  onClick={() => void copy(createdToken, "token")}
                >
                  {copiedToken ? (
                    <Check size={14} aria-hidden="true" />
                  ) : (
                    <Copy size={14} aria-hidden="true" />
                  )}
                  {copiedToken ? "Copiato" : "Copia token"}
                </button>
                <button
                  type="button"
                  className="secondary small-button"
                  onClick={() =>
                    void copy(
                      `Authorization: Bearer ${createdToken}`,
                      "header",
                    )
                  }
                >
                  {copiedHeader ? (
                    <Check size={14} aria-hidden="true" />
                  ) : (
                    <Copy size={14} aria-hidden="true" />
                  )}
                  {copiedHeader ? "Copiato" : "Copia header"}
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
          )}

          <div className="mcp-token-toolbar">
            <div>
              <h3>Token dei client</h3>
              <p className="muted small">
                Un token per client. La revoca è immediata.
              </p>
            </div>
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
            <div className="mcp-create">
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
            <div className="mcp-token-list">
              {tokens.map((token) => (
                <div className="mcp-token-row" key={token.id}>
                  <div className="mcp-token-main">
                    <strong>{token.name}</strong>
                    <span className="muted small">
                      {token.prefix}… · ultimo uso {formatMoment(token.last_used_at)}
                      {token.revoked_at ? " · revocato" : ""}
                    </span>
                  </div>
                  <span className="badge">
                    {Object.keys(token.permissions).length} operazioni
                  </span>
                  <button
                    type="button"
                    className="secondary small-button"
                    onClick={() => selectToken(token)}
                    disabled={busy || Boolean(token.revoked_at)}
                  >
                    Gestisci
                  </button>
                </div>
              ))}
            </div>
          )}

          {selected && (
            <div className="mcp-permissions">
              <div className="mcp-permissions-head">
                <div>
                  <h3>Permessi di {selected.name}</h3>
                  <p className="muted small">
                    {Object.keys(draft).length} di {totalOperations} operazioni
                    attive. Le modifiche valgono dopo il salvataggio.
                  </p>
                </div>
                <div className="mcp-search">
                  <Search size={16} aria-hidden="true" />
                  <input
                    type="search"
                    value={permissionQuery}
                    onChange={(event) => setPermissionQuery(event.target.value)}
                    placeholder="Cerca operazione"
                    aria-label="Cerca operazione MCP"
                  />
                </div>
              </div>

              <div className="mcp-area-grid">
                {visibleAreas.map((area) => {
                  const Icon = AREA_ICONS[area.area] ?? Plug;
                  const enabled = area.operations.filter(
                    (operation) => draft[operation.id],
                  ).length;
                  return (
                    <div className="mcp-area-card" key={area.area}>
                      <div className="mcp-area-head">
                        <div className="mcp-area-title">
                          <Icon size={17} aria-hidden="true" />
                          <span>{area.area}</span>
                          <span className="badge">{enabled}</span>
                        </div>
                        <div className="mcp-area-actions">
                          <button
                            type="button"
                            className="link-button"
                            onClick={() => enableReads(area)}
                            disabled={busy || !area.operations.some((op) => op.kind === "read")}
                          >
                            Letture
                          </button>
                          <button
                            type="button"
                            className="link-button"
                            onClick={() => disableArea(area)}
                            disabled={busy}
                          >
                            Disattiva
                          </button>
                        </div>
                      </div>
                      <div className="mcp-operation-list">
                        {area.operations.map((operation) => (
                          <div className="mcp-operation" key={operation.id}>
                            <div className="mcp-operation-text">
                              <span>{operation.label}</span>
                              <span className="mcp-operation-kind">
                                {operation.kind === "read" ? "Lettura" : "Scrittura"}
                              </span>
                            </div>
                            <div
                              className="mcp-level"
                              role="group"
                              aria-label={`Permesso per ${operation.label}`}
                            >
                              <button
                                type="button"
                                className={!draft[operation.id] ? "active" : ""}
                                aria-pressed={!draft[operation.id]}
                                onClick={() => setLevel(operation.id, "off")}
                                disabled={busy}
                              >
                                Off
                              </button>
                              <button
                                type="button"
                                className={draft[operation.id] ? "active" : ""}
                                aria-pressed={Boolean(draft[operation.id])}
                                onClick={() => setLevel(operation.id, operation.kind)}
                                disabled={busy}
                              >
                                {operation.kind === "read" ? "Lettura" : "Scrittura"}
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>

              {visibleAreas.length === 0 && (
                <p className="muted small">Nessuna operazione trovata.</p>
              )}

              <div className="mcp-save-bar">
                <label>
                  Password attuale per salvare
                  <input
                    type="password"
                    autoComplete="current-password"
                    value={permissionPassword}
                    onChange={(event) => setPermissionPassword(event.target.value)}
                  />
                </label>
                <div className="mcp-save-actions">
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
              </div>

              {!revoking ? (
                <button
                  type="button"
                  className="danger small-button mcp-revoke"
                  onClick={() => setRevoking(true)}
                  disabled={busy}
                >
                  <Trash2 size={14} aria-hidden="true" /> Revoca token
                </button>
              ) : (
                <div className="mcp-revoke-panel">
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
