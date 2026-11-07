import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type TrashItem, type TrashType } from "../api";
import { ConfirmModal } from "../components/ConfirmModal";
import { useToast } from "../components/Toast";

const TYPE_LABELS: Record<TrashType, string> = {
  movement: "Movimenti",
  account: "Conti",
  savings: "Salvadanai",
  automation: "Automazioni",
  position: "Posizioni",
  operation: "Operazioni",
  category: "Categorie",
  tag: "Tag",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  });
}

export function TrashPage() {
  const { notify } = useToast();
  const [items, setItems] = useState<TrashItem[]>([]);
  const [filterType, setFilterType] = useState<"" | TrashType>("");
  const [filterFrom, setFilterFrom] = useState("");
  const [filterTo, setFilterTo] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmPurge, setConfirmPurge] = useState<TrashItem | null>(null);
  const [confirmEmpty, setConfirmEmpty] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.trash(filterType || undefined);
      setItems(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, [filterType]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleRestore(item: TrashItem) {
    setError(null);
    setBusy(true);
    try {
      await api.restoreTrash(item.type, item.id);
      notify(`«${item.label}» ripristinato.`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ripristino non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function handlePurge(item: TrashItem) {
    setError(null);
    setBusy(true);
    try {
      await api.purgeTrash(item.type, item.id);
      notify("Elemento eliminato definitivamente.");
      setConfirmPurge(null);
      await load();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Eliminazione non riuscita.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleEmpty() {    setError(null);
    setBusy(true);
    try {
      const result = await api.emptyTrash();
      notify(`Cestino svuotato (${result.purged} elementi).`);
      setConfirmEmpty(false);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  const visibleItems = items.filter((item) => {
    if (!filterFrom && !filterTo) return true;
    if (!item.deleted_at) return false;
    const day = item.deleted_at.slice(0, 10);
    if (filterFrom && day < filterFrom) return false;
    if (filterTo && day > filterTo) return false;
    return true;
  });
  const hasFilters = Boolean(filterType || filterFrom || filterTo);

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Cestino</p>
          <h1>Elementi eliminati</h1>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            className="danger"
            disabled={busy}
            onClick={() => setConfirmEmpty(true)}
          >
            Svuota cestino
          </button>
        )}
      </section>

      {error && <p className="error">{error}</p>}

      <section className="card">
        <div className="filters">
          <label>
            <span className="small muted">Tipo</span>
            <select
              value={filterType}
              onChange={(event) =>
                setFilterType(event.target.value as "" | TrashType)
              }
            >
              <option value="">Tutti i tipi</option>
              {(Object.keys(TYPE_LABELS) as TrashType[]).map((type) => (
                <option key={type} value={type}>
                  {TYPE_LABELS[type]}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span className="small muted">Dal</span>
            <input
              type="date"
              value={filterFrom}
              onChange={(event) => setFilterFrom(event.target.value)}
            />
          </label>
          <label>
            <span className="small muted">Al</span>
            <input
              type="date"
              value={filterTo}
              onChange={(event) => setFilterTo(event.target.value)}
            />
          </label>
          {hasFilters && (
            <div className="actions">
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setFilterType("");
                  setFilterFrom("");
                  setFilterTo("");
                }}
              >
                Mostra tutto
              </button>
            </div>
          )}
        </div>
        {loading ? (
          <p className="muted">Caricamento…</p>
        ) : items.length === 0 ? (
          <p className="muted">Il cestino è vuoto.</p>
        ) : visibleItems.length === 0 ? (
          <p className="muted">Nessun elemento per questo filtro.</p>
        ) : (
          <ul className="entity-list">
            {visibleItems.map((item) => (
              <li key={`${item.type}-${item.id}`}>
                <div>
                  <strong>{item.label}</strong>
                  <span className="muted small">
                    {" "}
                    · {TYPE_LABELS[item.type]} · eliminato il{" "}
                    {formatDate(item.deleted_at)}
                    {item.deleted_by ? ` · da ${item.deleted_by}` : ""}
                  </span>
                </div>
                <span className="entity-side">
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy}
                    onClick={() => void handleRestore(item)}
                  >
                    Ripristina
                  </button>
                  <button
                    type="button"
                    className="danger"
                    disabled={busy}
                    onClick={() => setConfirmPurge(item)}
                  >
                    Elimina
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <p className="muted small">
        <Link to="/movements">Torna al registro</Link>
      </p>

      {confirmPurge && (
        <ConfirmModal
          title="Eliminare definitivamente?"
          summary={[
            `«${confirmPurge.label}» (${TYPE_LABELS[confirmPurge.type]}).`,
            "L'eliminazione definitiva non si può annullare.",
          ]}
          busy={busy}
          onConfirm={() => void handlePurge(confirmPurge)}
          onCancel={() => setConfirmPurge(null)}
        />
      )}
      {confirmEmpty && (
        <ConfirmModal
          title="Svuotare il cestino?"
          summary={[
            `Tutti gli ${items.length} elementi saranno eliminati definitivamente.`,
            "L'operazione non si può annullare.",
          ]}
          busy={busy}
          onConfirm={() => void handleEmpty()}
          onCancel={() => setConfirmEmpty(false)}
        />
      )}
    </div>
  );
}
