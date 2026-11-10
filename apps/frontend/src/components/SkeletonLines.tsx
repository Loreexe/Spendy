/**
 * Segnaposto di caricamento: righe o card con la classe `.skeleton` già
 * esistente. Il contenitore è una regione `status` con etichetta annunciata
 * dai lettori di schermo; i blocchi animati restano decorativi.
 */
const LINE_WIDTHS = ["100%", "92%", "78%", "96%", "84%"];

export function SkeletonLines({
  rows = 3,
  variant = "lines",
  label = "Caricamento in corso",
}: {
  rows?: number;
  variant?: "lines" | "cards";
  label?: string;
}) {
  const count = Math.max(1, rows);
  return (
    <div
      className="skeleton-lines"
      data-variant={variant}
      role="status"
      aria-label={label}
    >
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={variant === "cards" ? "skeleton skeleton-card" : "skeleton skeleton-line"}
          style={
            variant === "lines"
              ? { width: LINE_WIDTHS[index % LINE_WIDTHS.length] }
              : undefined
          }
          aria-hidden="true"
        />
      ))}
    </div>
  );
}
