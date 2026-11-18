import { useCallback, useEffect, useState } from "react";
import { LogOut, ShieldCheck } from "lucide-react";
import { api, type SessionInfo } from "../api";
import { ConfirmModal } from "./ConfirmModal";
import { InlineMessage } from "./InlineMessage";
import { SkeletonLines } from "./SkeletonLines";

function matches(query: string, keywords: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return keywords.toLowerCase().includes(needle);
}

function hours(seconds: number): string {
  return (seconds / 3600).toLocaleString("it-IT", {
    maximumFractionDigits: 1,
  });
}

export function SessionsSection({ query }: { query: string }) {
  const [info, setInfo] = useState<SessionInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      setInfo(await api.sessions());
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Sessioni non disponibili.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function revokeOthers() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await api.revokeOtherSessions();
      setConfirm(false);
      setMessage(
        result.revoked_sessions === 1
          ? "1 sessione terminata."
          : `${result.revoked_sessions} sessioni terminate.`,
      );
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Revoca non riuscita.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!matches(query, "sessioni sessione sicurezza accesso dispositivi inattività")) {
    return null;
  }

  return (
    <section className="profile-section">
      <div className="section-heading">
        <h2>Sessioni</h2>
        <ShieldCheck size={18} aria-hidden="true" />
      </div>
      {loading ? (
        <SkeletonLines rows={2} label="Caricamento sessioni" />
      ) : (
        <>
          {error && <InlineMessage tone="error">{error}</InlineMessage>}
          {message && <InlineMessage tone="success">{message}</InlineMessage>}
          {info && (
            <div className="stack">
              <p className="muted small">
                La sessione web dura al massimo {hours(info.session_cookie_age)}{" "}
                ore e viene chiusa dopo {hours(info.idle_timeout)} ore di
                inattività. Il cambio password termina le altre sessioni.
              </p>
              <p>
                Altre sessioni attive: <strong>{info.other_sessions}</strong>
              </p>
              <div className="pairing-actions">
                <button
                  type="button"
                  className="danger small-button"
                  onClick={() => setConfirm(true)}
                  disabled={busy || info.other_sessions === 0}
                >
                  <LogOut size={14} aria-hidden="true" /> Termina le altre
                  sessioni
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {confirm && (
        <ConfirmModal
          title="Terminare le altre sessioni?"
          summary={[
            "Le sessioni web aperte su altri browser verranno chiuse.",
            "Questa sessione resterà attiva.",
          ]}
          confirmLabel="Termina"
          busyLabel="Termino…"
          busy={busy}
          onConfirm={() => void revokeOthers()}
          onCancel={() => setConfirm(false)}
        />
      )}
    </section>
  );
}
