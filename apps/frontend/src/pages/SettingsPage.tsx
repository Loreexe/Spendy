import { useEffect, useState } from "react";
import { Monitor, Moon, Search, Sun, X } from "lucide-react";
import { api } from "../api";
import { useAuth } from "../auth";
import { applyTheme, type Theme } from "../theme";
import { DevicesSection } from "../components/DevicesSection";
import { ImportExportSection } from "../components/ImportExportSection";

function matches(query: string, keywords: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return keywords.toLowerCase().includes(needle);
}

const THEME_CHOICES: { value: Theme; label: string; icon: typeof Moon }[] = [
  { value: "dark", label: "Scuro", icon: Moon },
  { value: "light", label: "Chiaro", icon: Sun },
  { value: "system", label: "Sistema", icon: Monitor },
];

function AppearanceSection({ query }: { query: string }) {
  const [theme, setTheme] = useState<Theme | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .profile()
      .then((profile) => setTheme(profile.theme))
      .catch(() =>
        setError("Preferenza del tema non caricata: resta quella attiva."),
      );
  }, []);

  async function choose(next: Theme) {
    if (next === theme) return;
    setError(null);
    setBusy(true);
    try {
      const updated = await api.updateTheme(next);
      setTheme(updated.theme);
      applyTheme(updated.theme);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Salvataggio del tema non riuscito.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (!matches(query, "aspetto tema scuro chiaro sistema interfaccia colori")) {
    return null;
  }

  return (
    <section className="profile-section">
      <div className="section-heading">
        <h2>Aspetto</h2>
      </div>
      <div
        className="theme-choices"
        role="radiogroup"
        aria-label="Tema dell'interfaccia"
      >
        {THEME_CHOICES.map(({ value, label, icon: Icon }) => (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={theme === value}
            className={`theme-choice${theme === value ? " selected" : ""}`}
            disabled={busy || theme === null}
            onClick={() => void choose(value)}
          >
            <Icon size={20} aria-hidden="true" />
            <span>{label}</span>
          </button>
        ))}
      </div>
      {error && <p className="error">{error}</p>}
    </section>
  );
}

export function SettingsPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");

  if (!user) return null;

  const appearance = matches(
    query,
    "aspetto tema scuro chiaro sistema interfaccia colori",
  );
  const data = matches(
    query,
    "import export esporta ripristina archivio csv backup importa movimenti zip",
  );
  const devices = matches(
    query,
    "dispositivi device qr pairing token revoca accesso telefono",
  );
  const nothing = !appearance && !data && !devices;

  return (
    <div className="stack-page profile-page">
      <section className="settings-intro">
        <div className="settings-intro-text">
          <p className="eyebrow">Account</p>
          <h1>Impostazioni</h1>
        </div>
        <div className="settings-search">
          <Search size={18} aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Cerca tra le impostazioni"
            aria-label="Cerca tra le impostazioni"
          />
          {query && (
            <button
              type="button"
              className="search-clear"
              aria-label="Cancella ricerca"
              onClick={() => setQuery("")}
            >
              <X size={16} aria-hidden="true" />
            </button>
          )}
        </div>
      </section>

      {!user.is_global_admin && <AppearanceSection query={query} />}

      {!user.is_global_admin && <DevicesSection query={query} />}

      {!user.is_global_admin && <ImportExportSection query={query} />}

      {nothing && (
        <p className="muted">
          Nessuna impostazione trovata per «{query.trim()}».
        </p>
      )}
    </div>
  );
}
