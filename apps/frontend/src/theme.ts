import { api } from "./api";

export type Theme = "dark" | "light";

const KEY = "spendy-theme";

function isTheme(value: unknown): value is Theme {
  return value === "dark" || value === "light";
}

/** Tema iniziale: preferenza locale o scuro di default (mai "auto"). */
export function getInitialTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(KEY);
    if (isTheme(stored)) return stored;
  } catch {
    // localStorage non disponibile: si usa il default.
  }
  return "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem(KEY, theme);
  } catch {
    // Persistenza non disponibile: il tema resta applicato alla sessione.
  }
}

/**
 * Allinea il tema alla preferenza salvata nel profilo (solo account con
 * profilo; l'admin globale non ne ha). Silenzioso in caso di errore.
 */
export async function syncThemeFromProfile(): Promise<void> {
  try {
    const profile = await api.profile();
    if (isTheme(profile.theme)) applyTheme(profile.theme);
  } catch {
    // Profilo non raggiungibile: resta il tema corrente.
  }
}
