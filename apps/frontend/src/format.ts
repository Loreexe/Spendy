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
