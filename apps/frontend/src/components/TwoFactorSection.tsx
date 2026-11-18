import { useEffect, useState } from "react";
import { Check, Copy, KeyRound, ShieldCheck, ShieldOff } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import {
  api,
  type TwoFactorSetup,
  type TwoFactorStatus,
} from "../api";
import { useAuth } from "../auth";
import { QR_INK, QR_SURFACE } from "../theme";
import { InlineMessage } from "./InlineMessage";
import { SkeletonLines } from "./SkeletonLines";

function matches(query: string, keywords: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return keywords.toLowerCase().includes(needle);
}

function formatMoment(value: string | null): string {
  if (!value) return "—";
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

type PendingAction = "disable" | "regenerate" | null;

export function TwoFactorSection({ query }: { query: string }) {
  const { refresh } = useAuth();
  const [status, setStatus] = useState<TwoFactorStatus | null>(null);
  const [setup, setSetup] = useState<TwoFactorSetup | null>(null);
  const [confirmCode, setConfirmCode] = useState("");
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [action, setAction] = useState<PendingAction>(null);
  const [password, setPassword] = useState("");
  const [actionCode, setActionCode] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api
      .twoFactorStatus()
      .then(setStatus)
      .catch(() =>
        setError("Stato della verifica a due fattori non disponibile."),
      )
      .finally(() => setLoading(false));
  }, []);

  function resetPanels() {
    setSetup(null);
    setAction(null);
    setPassword("");
    setActionCode("");
    setConfirmCode("");
    setError(null);
  }

  async function loadStatus() {
    const updated = await api.twoFactorStatus();
    setStatus(updated);
    await refresh();
  }

  async function startSetup() {
    setBusy(true);
    setError(null);
    setMessage(null);
    setRecoveryCodes(null);
    try {
      setSetup(await api.startTwoFactorSetup());
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Configurazione non avviata.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function confirmSetup() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.confirmTwoFactor(confirmCode.trim());
      setRecoveryCodes(result.recovery_codes);
      setSetup(null);
      setConfirmCode("");
      await loadStatus();
      setMessage("Verifica a due fattori attivata.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Codice non valido.");
    } finally {
      setBusy(false);
    }
  }

  async function runAction() {
    if (!action) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      if (action === "disable") {
        await api.disableTwoFactor(password, actionCode.trim());
        setRecoveryCodes(null);
        setAction(null);
        await loadStatus();
        setMessage("Verifica a due fattori disattivata.");
      } else {
        const result = await api.regenerateRecoveryCodes(
          password,
          actionCode.trim(),
        );
        setRecoveryCodes(result.recovery_codes);
        setAction(null);
        await loadStatus();
        setMessage("Nuovi codici di recupero generati.");
      }
      setPassword("");
      setActionCode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function copyCodes() {
    if (!recoveryCodes) return;
    try {
      await navigator.clipboard.writeText(recoveryCodes.join("\n"));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Copia non disponibile: seleziona i codici manualmente.");
    }
  }

  if (!matches(query, "sicurezza 2fa due fattori autenticazione codice recupero")) {
    return null;
  }

  return (
    <section className="profile-section">
      <div className="section-heading">
        <h2>Sicurezza</h2>
        {status?.enabled && (
          <span className="badge">
            <ShieldCheck size={14} aria-hidden="true" /> Attiva
          </span>
        )}
      </div>
      <p className="muted small">
        La verifica a due fattori protegge l'accesso al pannello di
        amministrazione con un codice temporaneo generato da un'app di
        autenticazione.
      </p>

      {loading ? (
        <SkeletonLines rows={2} label="Caricamento sicurezza" />
      ) : (
        <>
          {error && <InlineMessage tone="error">{error}</InlineMessage>}
          {message && <InlineMessage tone="success">{message}</InlineMessage>}

          {recoveryCodes && (
            <div className="pairing-box">
              <div className="pairing-details">
                <strong>Codici di recupero</strong>
                <p className="muted small">
                  Ogni codice funziona una sola volta. Salvali in un posto
                  sicuro: non verranno mostrati di nuovo.
                </p>
                <div className="stack">
                  {recoveryCodes.map((recovery) => (
                    <code className="pairing-code" key={recovery}>
                      {recovery}
                    </code>
                  ))}
                </div>
                <div className="pairing-actions">
                  <button
                    type="button"
                    className="secondary small-button"
                    onClick={() => void copyCodes()}
                  >
                    {copied ? (
                      <Check size={14} aria-hidden="true" />
                    ) : (
                      <Copy size={14} aria-hidden="true" />
                    )}
                    {copied ? "Copiati" : "Copia codici"}
                  </button>
                  <button
                    type="button"
                    className="ghost small-button"
                    onClick={() => setRecoveryCodes(null)}
                  >
                    Ho salvato i codici
                  </button>
                </div>
              </div>
            </div>
          )}

          {!status?.enabled && !setup && (
            <div className="pairing-actions">
              <button
                type="button"
                onClick={() => void startSetup()}
                disabled={busy}
              >
                <ShieldCheck size={16} aria-hidden="true" /> Attiva la 2FA
              </button>
            </div>
          )}

          {setup && (
            <div className="pairing-box">
              <div className="pairing-qr">
                <QRCodeSVG
                  value={setup.otpauth_uri}
                  size={190}
                  bgColor={QR_SURFACE}
                  fgColor={QR_INK}
                  level="M"
                  marginSize={2}
                  title="QR per la verifica a due fattori"
                />
              </div>
              <div className="pairing-details">
                <span className="stat-label">Segreto</span>
                <code className="pairing-code">{setup.secret}</code>
                <p className="muted small">
                  Scansiona il QR con l'app di autenticazione, oppure inserisci
                  il segreto a mano. Poi conferma con il codice a 6 cifre.
                </p>
                <label>
                  Codice di verifica
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={confirmCode}
                    onChange={(event) => setConfirmCode(event.target.value)}
                    required
                  />
                </label>
                <div className="pairing-actions">
                  <button
                    type="button"
                    onClick={() => void confirmSetup()}
                    disabled={busy || confirmCode.trim().length < 6}
                  >
                    <KeyRound size={16} aria-hidden="true" /> Conferma
                  </button>
                  <button
                    type="button"
                    className="ghost"
                    onClick={resetPanels}
                    disabled={busy}
                  >
                    Annulla
                  </button>
                </div>
              </div>
            </div>
          )}

          {status?.enabled && (
            <div className="stack">
              <p className="muted small">
                Attiva dal {formatMoment(status.confirmed_at)} · codici di
                recupero rimasti: {status.recovery_codes_remaining}
              </p>
              <div className="pairing-actions">
                <button
                  type="button"
                  className="secondary small-button"
                  onClick={() => {
                    setAction("regenerate");
                    setPassword("");
                    setActionCode("");
                    setError(null);
                  }}
                  disabled={busy}
                >
                  <KeyRound size={14} aria-hidden="true" /> Rigenera codici
                </button>
                <button
                  type="button"
                  className="danger small-button"
                  onClick={() => {
                    setAction("disable");
                    setPassword("");
                    setActionCode("");
                    setError(null);
                  }}
                  disabled={busy}
                >
                  <ShieldOff size={14} aria-hidden="true" /> Disattiva 2FA
                </button>
              </div>

              {action && (
                <div className="stack">
                  <p className="muted small">
                    {action === "disable"
                      ? "Per disattivare conferma la password e un codice di verifica o di recupero."
                      : "Per rigenerare i codici conferma la password e un codice di verifica o di recupero."}
                  </p>
                  <label>
                    Password attuale
                    <input
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      required
                    />
                  </label>
                  <label>
                    Codice di verifica o di recupero
                    <input
                      type="text"
                      value={actionCode}
                      onChange={(event) => setActionCode(event.target.value)}
                      required
                    />
                  </label>
                  <div className="pairing-actions">
                    <button
                      type="button"
                      className={action === "disable" ? "danger" : undefined}
                      onClick={() => void runAction()}
                      disabled={busy || !password || !actionCode.trim()}
                    >
                      {busy
                        ? "Operazione…"
                        : action === "disable"
                          ? "Disattiva"
                          : "Rigenera"}
                    </button>
                    <button
                      type="button"
                      className="ghost"
                      onClick={resetPanels}
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
