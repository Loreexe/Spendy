export function ConfirmModal({
  title,
  summary,
  confirmLabel = "Elimina",
  busy = false,
  onConfirm,
  onCancel,
}: {
  title: string;
  summary: string[];
  confirmLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <h2>{title}</h2>
        <ul className="stack">
          {summary.map((line, index) => (
            <li key={index} className="muted">
              {line}
            </li>
          ))}
        </ul>
        <div className="actions">
          <button
            type="button"
            className="danger"
            disabled={busy}
            onClick={onConfirm}
          >
            {busy ? "Eliminazione…" : confirmLabel}
          </button>
          <button
            type="button"
            className="secondary"
            disabled={busy}
            onClick={onCancel}
          >
            Annulla
          </button>
        </div>
      </div>
    </div>
  );
}
