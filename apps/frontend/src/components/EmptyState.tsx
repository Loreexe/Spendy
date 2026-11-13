import { useId } from "react";
import { ILLUSTRATIONS, type IllustrationId } from "./Illustrations";

/**
 * Stato vuoto: icona Lucide di grandi dimensioni, titolo, descrizione e CTA opzionale.
 * La CTA compare solo se sono presenti sia etichetta sia azione, così il
 * componente degrada bene anche senza azione.
 */
export function EmptyState({
  illustration,
  title,
  description,
  actionLabel,
  onAction,
}: {
  illustration: IllustrationId;
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  const titleId = useId();
  const Illustration = ILLUSTRATIONS[illustration];
  const hasAction = Boolean(actionLabel && onAction);

  return (
    <div className="empty-state" role="group" aria-labelledby={titleId}>
      <div className="empty-state-art" aria-hidden="true">
        <Illustration />
      </div>
      <p className="empty-state-title" id={titleId}>
        {title}
      </p>
      {description && <p className="empty-state-description">{description}</p>}
      {hasAction && (
        <button
          type="button"
          className="secondary empty-state-action"
          onClick={onAction}
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
