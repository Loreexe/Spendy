# Spendy — visualizzazione del design

Rappresentazione grafica di [`DESIGN.md`](../../DESIGN.md) (versione corrente **0.9.4**), riferita a
**Spendy 0.8.6** (12 novembre 2026) e al sistema di design di prodotto **web + Android**. I valori
vengono dai sorgenti reali: token CSS, costanti Compose, pacchetto logo, font self-hosted e icone
dell'app. Non è un asset di prodotto e non introduce decisioni nuove.

> **Tavola non rigenerata (2026-11-12):** i file `design-system*.html/png` e i dettagli non sono
> stati rigenerati e rappresentano ancora la release **0.8.3**: non includono Home al posto di
> Dashboard, il menu avatar con testata, le icone delle categorie, l'orario dei movimenti né le
> icone Lucide degli stati vuoti (DC-120). Vanno rigenerati con i comandi sotto prima di essere
> considerati allineati alla 0.8.6.

## File

| File | Cosa è |
| --- | --- |
| `design-system.html` | Tavola interattiva, **autonoma** (inter, logo e illustrazioni incorporati come data URI/SVG inline; nessuna richiesta esterna). Tema con `?theme=dark` o `?theme=light` (default: scuro, come l'app). |
| `design-system-dark.png` | Poster del tema scuro, 3200 × 21324 px (1600 px CSS a 2x). |
| `design-system-light.png` | Poster del tema chiaro, stesse dimensioni. |
| `detail-identita.png` | Dettaglio 2x: intestazione, logo, principio flat/mono. |
| `detail-token-tipografia.png` | Dettaglio 2x: tema e token, scala tipografica, cifre tabulari, formati. |
| `detail-componenti.png` | Dettaglio 2x: icone, struttura e pagine, Profilo/Impostazioni Android, componenti e feedback. |
| `detail-dashboard.png` | Dettaglio 2x: dashboard completa (metriche, andamento, Entrate vs uscite, categorie) e accessibilità. |
| `build/` | Sorgenti riproducibili: template, assemblatore, cattura CDP, verifica contrasti. |

## Mappa della tavola

| DESIGN.md | Pannello | Contenuto |
| --- | --- | --- |
| Logo | 01 | Simbolo, tre lockup, colore, taglie, flat/mono, pacchetto asset |
| Tema · Token e forma | 02 | Scuro/chiaro/Sistema, superfici, semantica, fondi soft AA, proiezione Android, raggi/motion/glow |
| Tipografia, cifre e formati | 03 | Inter 400–700, scala web e Compose, `.tnum`, format `1.234,56 €`, date |
| Icone e illustrazioni | 04 | Lucide web/Android, line art mint, empty state e regole |
| Struttura · Pagine · Componenti · Feedback | 05 | Topbar web a 6 voci + menu avatar (tavola non rigenerata: descrive la 0.8.3), bottom bar mobile, Android (tab, ⋮, FAB, swipe), mappa pagine, **Profilo/Impostazioni Android**, componenti e stati, **dashboard completa** con Entrate vs uscite, toast/notice/modale, tabelle, grafici |
| Accessibilità · i18n | 06 | AA su superfici e fondi soft, focus, tastiera, touch 44 px, motion, lingua/formati |

## Rigenerare

```bash
# 1. assembla HTML + font + logo + illustrazioni dal template
python3 docs/design/build/build_html.py

# 2. verifica i contrasti AA sui token reali (esce 1 se qualcosa scende sotto 4.5:1)
python3 docs/design/build/check_contrast.py

# 3. cattura il poster in strisce CDP (Chromium headless con debug remoto)
chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --allow-file-access-from-files --remote-debugging-port=9333 \
  --user-data-dir=/tmp/spendy-shot --window-size=1600,1200 \
  "file://$PWD/docs/design/design-system.html?theme=dark" &
sleep 4
node docs/design/build/render.js dark /tmp/spendy-slices 9333
```

Le strisce prodotte da `render.js` sono PNG da 3200 px di larghezza a scala 2x; vanno unite
verticalmente (ImageMagick `convert /tmp/spendy-slices/slice-*.png -append poster.png` o PIL).
La cattura a strisce esiste perché uno screenshot full-page di un documento alto ~10660 px CSS
supera i limiti di tile memory di Chromium e corrompe alcune aree. Ripetere con `?theme=light`
per la variante chiara.

## Fonti e vincoli

- `DESIGN.md` (fonte normativa pubblica) e `.spendy-wiki/UX.md` (decisioni private).
- `../design/` (livello operativo: catalogo componenti, layout, piattaforme, verifiche, stato) e
  `../design/checks/check_design.py` (controlli statici, eseguito anche in CI).
- Token: `apps/frontend/src/styles/tokens.css`; proiezione Android in `Color.kt`, `Theme.kt`, `Type.kt`.
- Logo: `apps/frontend/public/logo/` (pacchetto approvato, nessun font a runtime).
- Font: `apps/frontend/public/fonts/` (Inter, SIL OFL) — incorporati nell'HTML.
- Illustrazioni: `apps/frontend/src/components/Illustrations.tsx` (web); gli stessi sei soggetti
  sono vector drawable in Android (`res/drawable/ill_empty_*.xml`).
- Icone: le pathData canoniche sono quelle Android (`res/drawable/ic_lucide_*.xml`); web e tavola
  usano lo stesso set Lucide (Movimenti `receipt-text`, Automazioni `clock`, Profilo `user`, ecc.).
- Contrasti: calcolati sui token con la formula WCAG 2.x da `build/check_contrast.py`; i valori
  riportati nella tavola coincidono con l'esito dello script.
