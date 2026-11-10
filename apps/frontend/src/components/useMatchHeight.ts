import { useCallback, useEffect, useRef } from "react";

/**
 * Mantiene due card affiancate alla stessa altezza: il contenitore
 * (`setBox`) copia l'altezza del riferimento (`setReference`) e il suo
 * contenuto scorre dentro. Sotto i 761 px (layout impilato) non fa nulla.
 *
 * Usa callback ref: la sincronizzazione scatta all'attacco dei nodi,
 * senza dipendere dall'ordine degli effect (che con i gate di caricamento
 * può arrivare prima del montaggio).
 */
export function useMatchedHeight(enabled = true) {
  const boxRef = useRef<HTMLElement | null>(null);
  const refRef = useRef<HTMLElement | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);

  const apply = useCallback(() => {
    const boxed = boxRef.current;
    const reference = refRef.current;
    if (!enabled || !boxed || !reference) return;
    if (window.matchMedia("(min-width: 761px)").matches) {
      const height = `${reference.offsetHeight}px`;
      // Altezza e tetto insieme: la card gemella non può né restare più bassa
      // né crescere col contenuto (la lista interna scorre).
      boxed.style.height = height;
      boxed.style.maxHeight = height;
    } else {
      boxed.style.height = "";
      boxed.style.maxHeight = "";
    }
  }, [enabled]);

  useEffect(() => {
    const onChange = () => apply();
    const query = window.matchMedia("(min-width: 761px)");
    query.addEventListener("change", onChange);
    window.addEventListener("resize", onChange);
    observerRef.current = new ResizeObserver(onChange);
    if (refRef.current) observerRef.current.observe(refRef.current);
    apply();
    return () => {
      observerRef.current?.disconnect();
      observerRef.current = null;
      query.removeEventListener("change", onChange);
      window.removeEventListener("resize", onChange);
    };
  }, [apply]);

  const setBox = useCallback(
    (element: HTMLElement | null) => {
      boxRef.current = element;
      apply();
    },
    [apply],
  );

  const setReference = useCallback(
    (element: HTMLElement | null) => {
      refRef.current = element;
      if (element && observerRef.current) {
        observerRef.current.observe(element);
      }
      apply();
    },
    [apply],
  );

  return [setBox, setReference] as const;
}
