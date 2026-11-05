# Logo Spendy — pacchetto F1 (approvato 2026-11-05, gate G1–G4; lockup integrato approvato lo stesso giorno)

Sorgente: SVG base fornito dall'utente, normalizzato in `spendy-symbol.svg`
(viewBox `0 0 500 760`, mask con 2 fori simmetrici, nessuna dipendenza da font
o immagini). Colore primario confermato: **`#1DB48B`**.

Lockup **integrato**: negli **orizzontali** il simbolo sostituisce la S iniziale → `[logo]pendy`
(scritta "pendy" in Noto Sans Black, SIL OFL, convertita in path: nessun font
a runtime). I **verticali** restano simbolo + scritta per esteso "Spendy".
La wordmark standalone non è nel pacchetto.

## File

| File | Uso |
| --- | --- |
| `spendy-symbol.svg` | Simbolo primario `#1DB48B`, per fondi scuri (contrasto 7.31:1 su `#0B0F0D`, AA) |
| `spendy-symbol-on-light.svg` | Simbolo `#166047`, per fondi chiari (6.96:1 su `#F4F7F5`, AA) |
| `spendy-symbol-mono-white.svg` / `spendy-symbol-mono-black.svg` | Versioni a un colore |
| `spendy-lockup-h-black-*.svg` | Lockup integrato orizzontale `[logo]pendy` (simbolo al posto della S), nei 4 temi (`on-dark`, `on-light`, `mono-white`, `mono-black`) |
| `spendy-lockup-v-black-*.svg` | Lockup verticale (simbolo sopra, scritta per esteso "Spendy" sotto), negli stessi 4 temi |
| `favicon.svg` / `favicon-light.svg` + `favicon-16/32/48.png` | Favicon (tassello scuro/chiaro + simbolo) |
| `pwa-512.svg` + `pwa-192.png` / `pwa-512.png` | Icona PWA full-bleed su `#0B0F0D` |
| `pwa-maskable.svg` + `pwa-maskable-512.png` | Icona maskable con padding di sicurezza |
| `og.svg` + `og-1200x630.png` | Immagine Open Graph (lockup integrato su `#0B0F0D`) |
| `android-foreground.svg` | Foreground adaptive icon (sfondo: `#0B0F0D`) |

## Note

- Gradiente: nessuno nel pacchetto (solo logo/login/hero per DC-084, da applicare in F2/F3).
- Le varianti con "Spendy" per esteso (wordmark piena, Medium) sono superate; i file di lavoro stanno in `/tmp/opencode/spendy-logo/f1/`.
- **Cablaggio non fatto in F1**: `index.html` (favicon/manifest/OG), `Layout.tsx` (brand) e manifest PWA si fanno in F3/F11.
- Licenza font: Noto Sans Black (SIL OFL), incorporata come path vettoriali.
