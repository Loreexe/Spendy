# Token — fonte autorevole

## Fonte

| Livello | File | Ruolo |
| --- | --- | --- |
| Web (CSS) | [`apps/frontend/src/styles/tokens.css`](../apps/frontend/src/styles/tokens.css) | **fonte autorevole** di colori, raggi, ombre, movimento, font |
| Web (consumo) | `apps/frontend/src/styles.css` e `apps/frontend/src/styles/*.css` | usano solo `var(--…)`; nessun valore di colore grezzo |
| Android (proiezione) | `apps/android/app/src/main/java/com/loreexe/spendy/ui/theme/Color.kt`, `Theme.kt`, `Type.kt` | proiezione degli stessi token in Compose, con i nomi `Spendy*` |

Non esiste `design/tokens/` perché lo stack ha già un tema centralizzato valido: creare una seconda
sede di token sarebbe un sistema parallelo. `DESIGN.md` §03 riporta i valori e i contrasti; questo
file descrive dove vivono, come si consumano e come si cambiano.

## Categorie e nomi (non valori)

I valori stanno in `tokens.css` e in `DESIGN.md` §03: qui non vengono ricopiati.

- **Superfici**: `--bg0`, `--bg1`, `--bg2`, `--line`; sfondo composto `--page-background` (definito
  in `styles.css` a partire da `--glow1`, `--glow2`, `--bg0`).
- **Testo**: `--text`, `--muted`.
- **Accento**: `--accent`, `--accent-ink`, `--accent-hover`, `--accent-soft`.
- **Semantica**: `--danger`, `--danger-soft`, `--warn`, `--warn-soft`, `--info`, `--up`, `--down`.
- **Aloni**: `--glow1`, `--glow2`.
- **Forma**: `--radius` (18 px), `--radius-lg` (20 px), `--radius-pill` (999 px).
- **Ombre e superfici fisse**: `--shadow-soft`, `--overlay`, `--scroll-shadow`, `--accent-glow`,
  `--warn-line`, `--qr-surface`.
- **Movimento**: `--motion-fast` (150 ms), `--motion-base` (200 ms).
- **Tipografia**: famiglie e pesi in `@font-face` (`tokens.css`) e in `Type.kt`; la scala non è
  tokenizzata (vedi sotto).

## Tipografia e spaziature

- **Font**: Inter self-hosted, pesi 400/500/600/700 in `apps/frontend/public/fonts/` (web) e
  `res/font/inter_*.ttf` (Android). Nessun altro font o peso.
- **Scala**: definita in `styles.css` (display, h2, body, label, importo, secondario, didascalia) e
  in `Type.kt` per Compose; i valori normativi sono in `DESIGN.md` §04. Non è un insieme di custom
  property: è una **convenzione osservata**.
- **Cifre tabulari**: `font-variant-numeric: tabular-nums` globale su `body` (styles.css) + utility
  `.tnum` per gli importi in tabelle e liste.
- **Spaziatura**: ritmo base 4 px (8/12/16/24/32) documentato in `DESIGN.md` §03, applicato con
  valori `rem` letterali nei CSS. Non esistono token di spaziatura: introdurli è una proposta
  aperta in [`decisions.md`](./decisions.md), non una regola approvata.

## Valori che vivono fuori dal CSS (allineamento obbligatorio)

Alcuni valori servono prima del CSS o dentro JavaScript; sono **mirror documentati** dei token:

| Dove | Cosa | Perché |
| --- | --- | --- |
| `apps/frontend/index.html` | `theme-color`, script pre-paint con i due `bg0` | il tema va risolto prima del primo frame, senza flash |
| `apps/frontend/src/theme.ts` | `THEME_COLOR`, `QR_SURFACE`, `QR_INK` | `meta theme-color` e QR SVG generato in JS |
| `apps/frontend/public/manifest.webmanifest` | `background_color`, `theme_color` | installazione PWA |

Questi valori **devono restare identici** ai token; `design/checks/check_design.py` li verifica e
fallisce se compaiono colori che non esistono in `tokens.css`. Non aggiungerne altri senza
aggiornare il controllo.

## Valori numerici intenzionali (eccezioni motivate)

Non sono violazioni: geometria specifica che non ha senso tokenizzare.

- `.app-main` max 1080 px (larghezza di lettura), `.card.narrow` max 420 px (accesso/setup).
- Altezze e spaziature dei grafici in `components/Charts.tsx` (geometria SVG) e nelle regole
  `.chart-*`.
- QR 190 px, avatar 44/96 px, logo e icone: taglie del componente.
- `--page-background` usa due radial-gradient con dimensioni in px: geometria dell'alone.

## Regole per modificare un token

1. Modifica `tokens.css` (tema scuro e chiaro).
2. Aggiorna la proiezione Android **nello stesso commit**; se la divergenza è intenzionale,
   documentala in [`platform-matrix.md`](./platform-matrix.md) e in [`decisions.md`](./decisions.md)
   (serve approvazione).
3. Esegui `python3 docs/design/build/check_contrast.py` e `python3 design/checks/check_design.py`.
4. Aggiorna `DESIGN.md` §03 (tabella e contrasti) e, se cambia l'identità, proponi la decisione
   all'utente prima di procedere.
5. Rigenera la tavola in `docs/design/` quando il valore è mostrato nella tavola (`build_html.py` +
   cattura, vedi `docs/design/README.md`).
6. Aggiorna `components.md`/`layout-rules.md` solo se cambia l'uso, non per ogni ritocco.

## Token consolidati in questa modifica (2026-11-10)

Nessun cambio di identità: sono valori già presenti nel codice, spostati in token per avere una
fonte unica e un controllo automatico.

| Token | Sostituisce | Nota |
| --- | --- | --- |
| `--radius-pill` | `border-radius: 999px` (17 occorrenze) | pillole, badge, switch, avatar |
| `--qr-surface` | `background: #ffffff` del QR | resta chiaro in entrambi i temi: il QR deve essere scansionabile |
| `--overlay` | `rgb(0 0 0 / 0.55)` del backdrop modale | superficie fissa |
| `--scroll-shadow` | `rgba(16, 24, 20, 0.25)` | ombra di scroll |
| `--accent-glow` | `rgb(29 180 139 / 0.4)` | alone del logo nell'hero |
| `--warn-line` | `rgba(138, 90, 18, 0.2)` | bordo del riquadro «in attesa» |

Sono elencati come **esistenti consolidati**, non come decisioni nuove: i valori visivi non
cambiano.
