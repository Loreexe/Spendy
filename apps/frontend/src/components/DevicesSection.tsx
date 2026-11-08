import { useCallback, useEffect, useState } from "react";
import {
  Check,
  Pencil,
  QrCode,
  RefreshCw,
  Smartphone,
  Trash2,
  X,
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import {
  api,
  type DevicePairing,
  type DeviceToken,
  type PairingCreated,
} from "../api";

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

const STATUS_LABEL: Record<string, string> = {
  pending: "In attesa del codice",
  claimed: "Da approvare",
  approved: "Approvato, in attesa del dispositivo",
  consumed: "Completato",
  rejected: "Rifiutato",
  expired: "Scaduto",
};

export function DevicesSection({ query }: { query: string }) {
  const [devices, setDevices] = useState<DeviceToken[]>([]);
  const [pairings, setPairings] = useState<DevicePairing[]>([]);
  const [created, setCreated] = useState<PairingCreated | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<number | null>(null);
  const [draft, setDraft] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      const [deviceResult, pairingResult] = await Promise.all([
        api.devices(),
        api.pairings(),
      ]);
      setDevices(deviceResult.devices);
      setPairings(pairingResult.pairings);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Elenco dei dispositivi non disponibile.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!created) return;
    const timer = window.setInterval(() => {
      api
        .pairings()
        .then((result) => setPairings(result.pairings))
        .catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [created]);

  async function generate() {
    setBusy(true);
    setError(null);
    try {
      const result = await api.createPairing();
      setCreated(result);
      await load();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Generazione del codice QR non riuscita.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function approve(pairing: DevicePairing) {
    setBusy(true);
    setError(null);
    try {
      await api.approvePairing(pairing.id);
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Approvazione non riuscita.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function reject(pairing: DevicePairing) {
    setBusy(true);
    setError(null);
    try {
      await api.rejectPairing(pairing.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rifiuto non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function revoke(device: DeviceToken) {
    if (
      !window.confirm(
        `Revocare «${device.name || "dispositivo"}»? Dovrà essere associato di nuovo.`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.revokeDevice(device.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Revoca non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function saveName(device: DeviceToken) {
    const name = draft.trim();
    if (!name) return;
    setBusy(true);
    setError(null);
    try {
      await api.renameDevice(device.id, name);
      setEditing(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Rinomina non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  if (!matches(query, "dispositivi device qr pairing token revoca accesso")) {
    return null;
  }

  return (
    <section className="profile-section">
      <div className="section-heading">
        <h2>Dispositivi</h2>
        <button
          type="button"
          className="secondary small-button"
          onClick={() => void load()}
          disabled={busy}
        >
          <RefreshCw size={14} aria-hidden="true" /> Aggiorna
        </button>
      </div>
      <p className="muted small">
        Dispositivi con un token di accesso. La sessione web corrente non
        compare in questo elenco.
      </p>

      {loading ? (
        <p className="muted">Caricamento dispositivi…</p>
      ) : devices.length === 0 ? (
        <p className="muted small">Nessun dispositivo associato.</p>
      ) : (
        <div className="device-list">
          {devices.map((device) => (
            <div className="device-row" key={device.id}>
              <span className="device-icon" aria-hidden="true">
                <Smartphone size={18} />
              </span>
              <div className="device-info">
                {editing === device.id ? (
                  <div className="device-rename">
                    <input
                      value={draft}
                      onChange={(event) => setDraft(event.target.value)}
                      aria-label="Nome del dispositivo"
                      maxLength={100}
                      autoFocus
                    />
                    <button
                      type="button"
                      className="icon-button"
                      aria-label="Salva nome"
                      onClick={() => void saveName(device)}
                      disabled={busy || !draft.trim()}
                    >
                      <Check size={16} />
                    </button>
                    <button
                      type="button"
                      className="icon-button"
                      aria-label="Annulla rinomina"
                      onClick={() => setEditing(null)}
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <>
                    <strong>
                      {device.name || "Dispositivo"}
                      {device.is_current && (
                        <span className="device-badge">questo</span>
                      )}
                    </strong>
                    <span className="device-meta">
                      {device.platform} · {device.prefix}… · creato il{" "}
                      {formatMoment(device.created_at)}
                    </span>
                    <span className="device-meta">
                      Ultimo uso: {formatMoment(device.last_used_at)}
                    </span>
                  </>
                )}
              </div>
              {editing !== device.id && (
                <div className="device-actions">
                  <button
                    type="button"
                    className="secondary small-button"
                    onClick={() => {
                      setEditing(device.id);
                      setDraft(device.name || "");
                    }}
                    disabled={busy}
                  >
                    <Pencil size={14} aria-hidden="true" /> Rinomina
                  </button>
                  <button
                    type="button"
                    className="danger small-button"
                    onClick={() => void revoke(device)}
                    disabled={busy}
                  >
                    <Trash2 size={14} aria-hidden="true" /> Revoca
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="section-heading pairing-heading">
        <h2>Aggiungi un dispositivo</h2>
      </div>
      <p className="muted small">
        Genera un codice monouso valido 5 minuti, inseriscilo sul nuovo
        dispositivo e approva la richiesta da qui.
      </p>
      <div className="pairing-actions">
        <button type="button" onClick={() => void generate()} disabled={busy}>
          <QrCode size={16} aria-hidden="true" /> Genera QR
        </button>
        {created && (
          <button
            type="button"
            className="secondary"
            onClick={() => setCreated(null)}
          >
            Chiudi QR
          </button>
        )}
      </div>

      {created && (
        <div className="pairing-box">
          <div className="pairing-qr">
            <QRCodeSVG
              value={created.qr_payload}
              size={190}
              bgColor="#ffffff"
              fgColor="#0B0F0D"
              level="M"
              marginSize={2}
              title="QR di associazione Spendy"
            />
          </div>
          <div className="pairing-details">
            <span className="stat-label">Codice</span>
            <code className="pairing-code">{created.code}</code>
            <span className="muted small">
              Scade alle {formatMoment(created.pairing.expires_at)}
            </span>
            <span className="muted small">
              Server: {created.server_url}
            </span>
            <span className="muted small">
              Sul nuovo dispositivo inserisci indirizzo e codice, poi approva
              qui.
            </span>
          </div>
        </div>
      )}

      {pairings.length > 0 && (
        <div className="pairing-list">
          {pairings.map((pairing) => (
            <div className="pairing-row" key={pairing.id}>
              <div className="device-info">
                <strong>
                  {pairing.new_device_name || "Nuovo dispositivo"}
                </strong>
                <span className="device-meta">
                  {pairing.new_device_platform} ·{" "}
                  {STATUS_LABEL[pairing.status] ?? pairing.status}
                </span>
                <span className="device-meta">
                  Richiesto il {formatMoment(pairing.created_at)}
                </span>
              </div>
              <div className="device-actions">
                <button
                  type="button"
                  className="small-button"
                  onClick={() => void approve(pairing)}
                  disabled={busy || pairing.status !== "claimed"}
                >
                  <Check size={14} aria-hidden="true" /> Approva
                </button>
                <button
                  type="button"
                  className="danger small-button"
                  onClick={() => void reject(pairing)}
                  disabled={busy}
                >
                  <X size={14} aria-hidden="true" /> Rifiuta
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p className="error">{error}</p>}
    </section>
  );
}
