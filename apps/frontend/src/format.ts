const euroFormat = new Intl.NumberFormat("it-IT", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
  useGrouping: true,
});

/** Importo in euro: raggruppamento sempre attivo, 2 decimali, NBSP prima di €. */
export function money(value: string | number): string {
  const number = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(number)) return "—";
  return `${euroFormat.format(number)}\u00A0€`;
}

export function signedMoney(value: string | number): string {
  const number = typeof value === "string" ? Number(value) : value;
  if (!Number.isFinite(number)) return "—";
  return `${number > 0 ? "+" : ""}${money(number)}`;
}

export function isoDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function todayISO(): string {
  return isoDate(new Date());
}

/** Data `gg/mm/aaaa` a partire da una data ISO `aaaa-mm-gg`. */
export function formatDate(iso: string): string {
  const date = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("it-IT");
}

/**
 * Ora `HH:MM` normalizzata; `null` se assente o non valida. Accetta anche
 * `HH:MM:SS`, come può arrivare da API non ancora allineate.
 */
export function normalizeTime(value?: string | null): string | null {
  if (!value) return null;
  const match = /^(\d{1,2}):(\d{2})(?::\d{2}(?:\.\d+)?)?$/.exec(value.trim());
  if (!match) return null;
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) return null;
  return `${String(hours).padStart(2, "0")}:${match[2]}`;
}

/** Ora corrente `HH:MM` nel fuso del browser (Europe/Rome per gli utenti Spendy). */
export function currentTimeHM(): string {
  const now = new Date();
  return `${String(now.getHours()).padStart(2, "0")}:${String(
    now.getMinutes(),
  ).padStart(2, "0")}`;
}

export function firstOfMonthISO(): string {
  const now = new Date();
  return isoDate(new Date(now.getFullYear(), now.getMonth(), 1));
}

export function amountClass(value: string | number): string {
  const number = typeof value === "string" ? Number(value) : value;
  if (number > 0) return "positive";
  if (number < 0) return "negative";
  return "";
}
