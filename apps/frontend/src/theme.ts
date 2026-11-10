import { api } from "./api";

export type Theme = "dark" | "light" | "system";
export type ResolvedTheme = "dark" | "light";

const KEY = "spendy-theme";
const MEDIA = "(prefers-color-scheme: light)";

/** Colori di sfondo del tema risolto, allineati a --bg0 in tokens.css. */
const THEME_COLOR: Record<ResolvedTheme, string> = {
  dark: "#0B0F0D",
  light: "#F4F7F5",
};

function isTheme(value: unknown): value is Theme {
  return value === "dark" || value === "light" || value === "system";
}

function systemTheme(): ResolvedTheme {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia(MEDIA).matches ? "light" : "dark";
}

/** Tiene allineato il meta theme-color della pagina al tema risolto. */
function syncThemeColor(resolved: ResolvedTheme): void {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", THEME_COLOR[resolved]);
}

/** Tema iniziale: preferenza locale o scuro di default. */
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
  const resolved = theme === "system" ? systemTheme() : theme;
  document.documentElement.dataset.theme = resolved;
  syncThemeColor(resolved);
  try {
    window.localStorage.setItem(KEY, theme);
  } catch {
    // Persistenza non disponibile: il tema resta applicato alla sessione.
  }
}

/**
 * Quando il tema segue il sistema, reagisce ai cambi del sistema operativo
 * senza ricaricare la pagina.
 */
export function watchSystemTheme(): void {
  if (typeof window === "undefined" || !window.matchMedia) return;
  window.matchMedia(MEDIA).addEventListener("change", () => {
    try {
      if (window.localStorage.getItem(KEY) === "system") {
        applyTheme("system");
      }
    } catch {
      // Nessuna preferenza leggibile: niente da aggiornare.
    }
  });
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
