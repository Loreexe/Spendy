import type { ReactNode } from "react";

export type InlineMessageTone = "success" | "warning" | "error";

/**
 * Messaggio inline per l'esito di form e sezioni (DESIGN.md §09):
 * `success` e `warning` sono i "notice" dentro la pagina/sezione, `error`
 * è l'errore esplicito accanto al campo o al form. Il componente produce lo
 * stesso markup dei blocchi scritti a mano (`.notice`/`.error`), così lo
 * stile resta in `styles/inline-message.css` e non viene duplicato nelle pagine.
 */
export function InlineMessage({
  tone = "success",
  children,
}: {
  tone?: InlineMessageTone;
  children: ReactNode;
}) {
  const className =
    tone === "error"
      ? "error"
      : tone === "warning"
        ? "notice warning"
        : "notice success";

  return <p className={className}>{children}</p>;
}
