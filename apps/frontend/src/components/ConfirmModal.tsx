import { useEffect, useId, useRef } from "react";

const FOCUSABLE =
  'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function ConfirmModal({
  title,
  summary,
  confirmLabel = "Elimina",
  busyLabel,
  busy = false,
  onConfirm,
  onCancel,
}: {
  title: string;
  summary: string[];
  confirmLabel?: string;
  busyLabel?: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const titleId = useId();
  const summaryId = useId();
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const cancelRef = useRef<HTMLButtonElement | null>(null);

  // Focus iniziale su "Annulla" e ripristino sull'elemento precedente.
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const cancel = cancelRef.current;
    if (cancel && !cancel.disabled) {
      cancel.focus();
    } else {
      dialogRef.current?.focus();
    }
    return () => {
      previous?.focus?.();
    };
  }, []);

  // Esc chiude; Tab e Shift+Tab ciclano dentro la finestra.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key !== "Tab") return;
      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusables = Array.from(
        dialog.querySelectorAll<HTMLElement>(FOCUSABLE),
      ).filter((element) => element.offsetParent !== null);
      if (focusables.length === 0) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;
      if (event.shiftKey) {
        if (active === first || !dialog.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last || !dialog.contains(active)) {
        event.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onCancel]);

  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div
        ref={dialogRef}
        className="modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={summaryId}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id={titleId}>{title}</h2>
        <ul className="stack" id={summaryId}>
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
            {busy ? (busyLabel ?? `${confirmLabel}…`) : confirmLabel}
          </button>
          <button
            ref={cancelRef}
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
