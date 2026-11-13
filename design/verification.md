# Verifiche

Controlli **esistenti** e realmente eseguibili. Non tutti sono automatici: quelli manuali vanno
dichiarati come tali. Lo stato riportato è l'ultima esecuzione conosciuta, non una promessa.

> **Release 0.8.4 (2026-11-11, pubblicata):** backend e web sono **verificati**;
> Android è **compilato e testato** ma **non provato su device/emulatore**. Gli esiti sono nella
> sezione dedicata; i limiti sono dichiarati e non vanno nascosti.
> **Release 0.8.6 (2026-11-13, pubblicata):** nuovo flusso movimento verificato su web (browser,
> creazione/eliminazione e modifica) e su Android (build, 31 test unitari, `lintDebug`, prova
> visuale sul telefono RMX5061 per i quattro passi). Il backend non è stato modificato.


## Comandi

| Controllo | Comando | Verifica | Stato 2026-11-11 |
| --- | --- | --- | --- |
| Typecheck + build web | `cd apps/frontend && npm run lint && npm run build` | TypeScript e bundle di produzione | **verde** (`0.8.4`, lint e build) |
| Contrasti AA token | `python3 docs/design/build/check_contrast.py` | 12 coppie testo/sfondo x 2 temi ≥ 4.5:1 | **verde** (tutte AA) |
| Controlli design system | `python3 design/checks/check_design.py` | token obbligatori, colori grezzi nei CSS, mirror JS/HTML, parità web↔Android, raggi, durate | **verde** (0 violazioni, 2 divergenze note documentate) |
| Versione allineata | `python3 scripts/check_version.py` (+ test dello script) | `VERSION` = package/Android | **verde**: 0.8.4 allineato |
| Backend | `cd apps/backend && python manage.py test` | suite Django (richiede PostgreSQL) | **verde**: 383 test (2026-11-11) |
| Android build/test/lint | `cd apps/android && ./gradlew :app:assembleDebug :app:testDebugUnitTest :app:lintDebug` | compilazione Compose, test unitari, lint, APK debug | **verde** (2026-11-11, 0.8.4: assembleDebug, **31 test**, lint 0 errori, APK debug); **prova su device/emulatore non eseguita** |
| Tavola grafica | `python3 docs/design/build/build_html.py` + cattura CDP (`docs/design/README.md`) | rigenerazione della rappresentazione | **non rigenerata** in questa sessione: la tavola statica descrive ancora la 0.8.3 |
| CI | `.github/workflows/ci.yml` (job `version`, `design-system`, `backend`, `frontend`), `android.yml` | gli stessi controlli in CI | il job `design-system` è nuovo: vale dal prossimo push, non eseguito qui |

## Verifica visiva eseguita (2026-11-10, percorso Profilo)

Verifica della prima applicazione concreta (`InlineMessage` nel Profilo), su server demo già attivo:

- Login reale su `http://127.0.0.1:5173` con l'utente demo, navigazione a `/account`, Chromium
  headless 156 via CDP (DevTools Protocol), screenshot temporanei poi rimossi (nessuna baseline
  aggiunta al repository).
- **390×844 (mobile), tema scuro e chiaro**: bottom bar fissa con icone + etichette e
  `safe-area`, form a colonna, nessun overflow orizzontale della pagina.
- **1440×900 (desktop), tema scuro**: topbar con 6 voci + avatar, contenuto entro `max-width`
  1080 px, campi su due colonne, footer con versione.
- **Temi**: il profilo demo ha il tema **chiaro** salvato; per la cattura scura il tema è stato
  applicato a runtime con `data-theme` (non salvato nel profilo). Sfondo letto da
  `getComputedStyle`: `rgb(11, 15, 13)` scuro, `rgb(244, 247, 245)` chiaro. Il cambio tema tramite
  l'interfaccia Impostazioni non è stato provato in questa sessione.
- **Stato di errore verificato** (non solo per equivalenza di markup): inviato il form «Cambia
  password» con password attuale errata; il backend ha risposto con l'errore validato e il Profilo ha
  mostrato `<InlineMessage tone="error">` («La password attuale non è corretta.») con colori letti da
  `getComputedStyle`: `rgb(242, 109, 109)` su `rgb(42, 21, 24)`, cioè `--danger` su `--danger-soft`
  del tema scuro; bottom bar non sovrapposta al messaggio.
- **Tono success non riprodotto** in questa sessione: produce lo stesso markup `.notice success` già
  usato in tutta l'app e il CSS è identico a quello precedente (solo spostato di file).
- **Non verificato**: client Android (nessuna build/emulatore in questa sessione).
- **Nota ambiente demo**: per le azioni autenticate usare `http://localhost:5173`, non
  `http://127.0.0.1:5173`: `CSRF_TRUSTED_ORIGINS` predefinito contiene `localhost:5173`, mentre da
  `127.0.0.1` le POST/PATCH autenticate falliscono con errore CSRF (comportamento preesistente, non
  introdotto da questa modifica).

Controllo negativo del `check_design.py`: aggiungendo temporaneamente una regola con colore grezzo,
raggio `999px` e durata `120ms`, lo script ha rilevato 3 violazioni ed è uscito con codice 1; il file
è stato ripristinato (hash verificato). Il controllo quindi non è un falso positivo permanente.

## Home — rifiniture da critique (2026-11-12, non rilasciate)

Critique Impeccable con due assessment isolati (design review + detector/evidenza browser) sulla **sola Home web**; correzioni approvate dall'utente e applicate in questa sessione. Verifiche eseguite sul server demo con Chromium headless 156 via CDP, viewport 1440×900, 768×1024 e 390×844, temi scuro e chiaro; nessuna baseline visiva aggiunta al repository.

| Controllo | Prova eseguita | Esito |
| --- | --- | --- |
| Typecheck + build web | `cd apps/frontend && npm run lint && npm run build` | **verde** |
| Contrasti AA token | `python3 docs/design/build/check_contrast.py` | **verde**: tutte le coppie ≥ 4.5:1 |
| Controlli design system | `python3 design/checks/check_design.py` | **verde**: 0 violazioni (2 divergenze note) |
| Detector Impeccable | `impeccable detect --json` su `DashboardPage.tsx` e `Charts.tsx` | **0 finding** (62 regole); il detector non legge CSS/JSX inline → falsi negativi possibili |
| 390×844 — overflow | `documentElement.scrollWidth` vs `clientWidth` | **390/390** in normale, vuoto, errore, aggiornamento (prima: 465/390) |
| 768×1024 e 1440×900 | stesse misure | **nessun overflow**; toolbar su una riga |
| Grafico Andamento | bounding box delle etichette SVG | etichette **≥11 px resi**: bbox 14 px a 390 (prima ≈5,4 px), 14 px a 768, 20 px a 1440; etichetta Y superiore interamente dentro l'SVG (padding superiore dinamico), nessuna sovrapposizione |
| Movimenti compatti — importi | DOM + colore calcolato | spese «−68,00 €», «−500,00 €», «−517,00 €» con `--down`; trasferimento «3,00 €» neutro; entrate «+»/`--up` (verificate dal codice e dalla convenzione Android, il dataset demo non ha entrate) |
| Movimenti compatti — righe | rect a 390 | righe 101,8 / 101,8 / 77,8 / 76,8 px: titolo troncato, importo e icona del tipo sulla stessa riga (Δy ≤ 4 px); prima la riga arrivava a 169,8 px e l'icona andava a capo |
| Conti — doppio importo | DOM | nota visibile «Saldo del periodo; tra parentesi il saldo attuale con i salvadanai»; «Saldo conti» della hero **neutro** |
| Stato vuoto | risposte dashboard/serie vuote | **3 `EmptyState`** (Conti, Salvadanai, Ultimi movimenti) con CTA «Crea conto», «Crea salvadanaio», «Registra movimento»; card grafici **assente**; nessun overflow |
| Stato di errore | risposte 500 | blocco `role="alert"` con «Riprova»; nessun dato residuo nell'errore iniziale; con dati già caricati compare la nota «I dati mostrati sono quelli dell'ultimo caricamento riuscito» |
| Caricamento iniziale | richieste dashboard sospese | skeleton dentro un unico `.dash-content[aria-busy="true"]` che riproduce le 5 card reali (hero, Grafici, Conti, Salvadanai, Ultimi movimenti) con `role="status"` «Caricamento della Home…»; altezze a 1440: 254/732/247/247/408 px contro 283/724/263/263/412 reali; a 390: 317/682/285/215/416 contro 355/651/308/199/436. Con setup/auth lenti la Home mostra lo stesso skeleton di pagina dalla prima pittura (`.dash-skeleton-pill`, `.dash-skeleton-amount`; nessuna `.loading-card`), status «Caricamento della Home…» |
| Aggiornamento periodo | richieste sospese dopo «Applica» | `.dash-content.is-updating` con `aria-busy="true"` e status live «Aggiornamento del periodo in corso…» |
| Filtri periodo e date | DOM + focus programmatico | `aria-pressed` true/false sui 4 preset; input data con `aria-label` «Data iniziale»/«Data finale»; focus visibile `outline 2px accent` con offset 2 dopo 2 rAF; target 44 px su pill, «Applica», «Riprova» e label data; voci bottom bar ≥44 px |
| Android | device/emulatore | **non eseguito** (nessun device in sessione): le modifiche sono solo web; il client Android ha già importi firmati e stati dedicati (dedotto dal codice, non verificato a runtime) |

Limiti dichiarati: nessuna prova con screen reader o tastiera reali (solo focus programmatico); `prefers-reduced-motion: reduce` forzato nelle catture; dataset demo unico (nessun importo negativo, conto archiviato o nome lungo); build di produzione non servita (Vite dev); nessuna baseline visiva. `design/components.md` e `DESIGN.md` sono in sola lettura nel workspace: l'aggiornamento del catalogo (`EmptyState` adottato in Home) e ogni ritocco identitario restano da fare quando i file saranno sbloccati; l'identità visiva non è cambiata.

## Skeleton di pagina — web (2026-11-12, non rilasciati)

Verifiche con Chromium headless via CDP, server demo, viewport 1440×900 e 390×844, temi scuro/chiaro; setup/auth tenuti in pausa per vedere il fallback di route e chiamate finance in pausa per il caricamento interno delle pagine.

| Controllo | Prova | Esito |
| --- | --- | --- |
| `npm run lint` / `npm run build` | build web | **verde** |
| Fallback di route | `/movements`, `/accounts`, `/settings`, `/investments` con setup/auth lenti | heading reale (Movimenti/Registro, Conti/Patrimonio, Impostazioni, Investimenti/Patrimonio), 2–5 card, 7–21 blocchi skeleton, **nessuna** `.loading-card` centrata, nessun overflow |
| Caricamento pagina | `/movements` e `/accounts` a 390 con chiamate finance sospese | skeleton della pagina (filtri/righe per Movimenti, form+elenco per Conti), 2 card, nessun overflow |
| Skeleton della Home | vedi sezione dedicata | invariato e verificato |
| Android | skeleton Compose al posto degli spinner | implementazione delegata e verificata con `assembleDebug` (vedi sezione Android) |

Limiti: la forma dello skeleton è una **approssimazione** delle card reali (numero di card e righe coerente, altezze non pixel-identiche); nessuna baseline visiva. `design/components.md` e `DESIGN.md` sono in sola lettura: manca la riga di catalogo per `PageSkeletons`.

## Skeleton di pagina — Android (2026-11-12, non rilasciati)

Implementazione delegata e verificata dal Lead con build; **nessuna prova su device/emulatore**.

| Controllo | Prova | Esito |
| --- | --- | --- |
| Build Android | `cd apps/android && source build/toolchain/env.sh && ./gradlew --console=plain :app:assembleDebug` | **BUILD SUCCESSFUL** (41 task; nessuna dipendenza nuova, versionName/versionCode invariati) |
| Componente | `ui/components/Skeleton.kt` | shimmer unico per pagina (`rememberInfiniteTransition` + `drawBehind`), statico in `LocalInspectionMode`, solo token (`surfaceVariant`/`primaryContainer`/`outline`), primitive e pagine `SpendyListSkeleton`, `SpendyFormSkeleton`/`SpendyProfileSkeleton`, `SpendyDashboardSkeleton`, `SpendyInlineSkeleton`; semantica «Caricamento…» con live region |
| Schermate coperte | 15 rami di caricamento sostituiti | Home dashboard, Accounts, Savings, Movements, Automations, Investments, Trash, Categories, Search, Devices, Profile (hero+sezioni), Data e Pairing (inline); error/empty e padding invariati |
| Non coperto (motivato) | loader d'azione | avatar upload/cambio password (spinner 18–20 dp nei bottoni), versione in Impostazioni, login in ServerFlow, boot `AppNavHost`: non sono caricamenti di pagina e non hanno uno stato di pagina da skeletonizzare |
| Limiti | device/emulatore | **non eseguito**: forme e shimmer non verificati a runtime su device; nessun `lintDebug` in questa sessione |

## Navbar «Minimal» (2026-11-10, DC-109)

- **Implementazione**: `ui/components/SpendyBottomBar.kt` (barra 60 dp + inset, senza linea/indicatore, etichette sempre visibili) con superficie piena e sfumatura di 16 dp in alto; `MainScreen` è passato da `Scaffold` a top bar + pager a tutta altezza + barra in overlay, con `LocalBottomBarInset` (72 dp) per contenuti e FAB.
- **Revisione**: il primo giro usava il blur reale (`rememberGraphicsLayer` + `BlurEffect`) con Compose 1.8.3; l'utente ha chiesto di toglierlo perché non gradito. Blur rimosso, superficie piena, Compose BOM riportato a **Compose 1.7.6** (BOM 2024.12.01).
- **Verifiche eseguite**: `assembleDebug` e `assembleRelease` verdi; 18 test unitari; `lintDebug` 0 errori; APK release firmato e **installato in place** sul telefono (`install -r`, `versionName 0.8.2`, dati conservati).
- **Verifica a schermo**: barra ancorata senza linea e senza blur, sfumatura in alto, tab Dashboard e Movimenti funzionanti, FAB sollevato sopra la barra, scorrimento del contenuto. **Non verificati**: TalkBack, scala del testo, tema chiaro e tablet/foldable.
- La preview locale della variante è `docs/design/navbar-lab-preview.html` (non tracciata), non è una verifica del client nativo.

## Release 0.8.4 — verifiche eseguite (2026-11-11)

Decisioni: DC-114…117. Esiti reali; dove non si è verificato qualcosa è dichiarato come limite.

| Controllo | Prova eseguita | Esito |
| --- | --- | --- |
| Backend — suite | `cd apps/backend && ../../.venv/bin/python manage.py test` | **verde: 383 test**, inclusi ora, ordinamento, icone, CSV e archivio schema 5 |
| Backend — migrazioni | `python manage.py makemigrations --check` | **verde**: nessuna migrazione mancante |
| Backend — API dal vivo | ambiente demo (`scripts/demo_server.sh`) | `time` in `HH:MM`; `POST` senza ora = ora corrente `Europe/Rome`; `PATCH` senza ora invariata; `icon` in categorie, movimenti e serie; migrazione demo con movimenti a 12:00 e icone predefinite |
| CSV / archivio | export e import dal vivo | export 6 colonne, import 5 e 6 colonne, template a 6 colonne; archivio schema 5 con `movimenti.csv` + `ora` e `categorie.csv` + `icona`; ripristino schemi 1–4 |
| Web — typecheck + build | `npm run lint && npm run build` | **verde** |
| Web — controlli design | `check_design.py`, `check_contrast.py` | **verdi** (0 violazioni; 2 divergenze note già documentate) |
| Web — visiva 390×844 | ispezione reale, temi scuro e chiaro | Home in colonna (hero → wallet/popover → azioni rapide → ultimi 3 movimenti → Entrate/Uscite → Andamento → Categorie), menu avatar con testata, campo Ora, profilo con foto; nessun overflow |
| Web — visiva 1440×900 | ispezione reale, temi scuro e chiaro | topbar a 6 voci con Home, popover conti, azione `+ Movimento` che apre `/movements` con Spesa preselezionata, tre card separate nell'ordine previsto |
| Android — build/test/lint | `./gradlew :app:assembleDebug :app:testDebugUnitTest :app:lintDebug` | **verde**: assembleDebug, **31 test**, lint 0 errori; versione 0.8.4/versionCode 5, APK debug prodotto |
| Versione | `python3 scripts/check_version.py` | **verde**: 0.8.4 allineato |
| Tastiera web — `CategorySelect`/`CategoryIconPicker` | prova completa da browser | **non eseguita**: solo build/API e ispezione visiva → limite dichiarato |
| Wizard di import da browser | prova completa del flusso | **non eseguito**: verificato via API/build → limite dichiarato |
| Android — runtime | device/emulatore | **non eseguito** (assente in sessione, no KVM): migrazione Room 6→7, upload/rimozione foto e flussi UI **non provati a runtime** → limite dichiarato |

Note obbligatorie:

- I test browser **non** dimostrano il client Android e viceversa.
- Nessuna baseline visiva è approvata: gli screenshot non sono riferimenti di regressione.
- La tavola `docs/design/` **non è stata rigenerata** in questa sessione: rappresenta ancora la 0.8.3.
- La `0.8.4` è pubblicata con tag `v0.8.4`; l'aggiornamento dell'LXC resta in carico all'utente.

## Scenari manuali per ogni modifica UI

Eseguire almeno quelli pertinenti alla modifica; dichiarare quelli saltati e perché.

| Scenario | Cosa controllare |
| --- | --- |
| Larghezza stretta (390×844) | bottom bar non copre contenuti/toast, testi lunghi vanno a capo, niente scroll orizzontale della pagina |
| Larghezza media (768×1024) | griglie a 2 colonne, nessun salto di layout tra 760 e 900 |
| Larghezza larga (1440×900) | `.app-main` max 1080, gerarchia e allineamenti |
| Temi | scuro, chiaro e «Sistema»; nessun flash al primo paint; `theme-color` coerente |
| Stati | hover (dove c'è puntatore), focus visibile da tastiera, disabled, caricamento (skeleton), errore, vuoto, successo |
| Tastiera | Tab raggiunge tutto, `Esc` chiude menu/modali, focus trap nella modale, focus restituito |
| Ingrandimento | zoom 200% e testo lungo: nessun contenuto tagliato o sovrapposto |
| Movimento | `prefers-reduced-motion: reduce`: animazioni e scroll morbido disattivati |
| Accessibilità | contrasto, etichette, ruoli (`dialog`, `status`), icone degli stati vuoti `aria-hidden`, target ≥ 44 px |
| Android (se toccato) | emulatore/dispositivo reale, TalkBack, scala font, tema Sistema; non basta il browser |

## Cosa non esiste (non dichiararlo come verificato)

- **Nessun test unitario/end-to-end frontend**: non c'è Vitest/Playwright/Jest; `npm test` non esiste.
- **Nessuna baseline visiva approvata**: gli screenshot in `docs/screenshots/` sono dimostrativi, non
  riferimenti di regressione. Non aggiornarli per far passare un controllo.
- **Nessuna verifica automatica di accessibilità** (axe o simili) e nessun test su emulatore nella
  CI: `android.yml` compila, testa e fa lint, ma non esegue l'app.
- **Nessun service worker**: non c'è nulla da verificare offline.

Introdurre test frontend o baseline visive richiede **nuove dipendenze e approvazione**
(proposta P-5 in [`decisions.md`](./decisions.md)).

## Regole

1. Usa prima gli strumenti esistenti; aggiungine uno solo se giustificato e approvato.
2. Non dichiarare una verifica non eseguita: distingui verde, non eseguito e limite noto.
3. I test browser non dimostrano il client Android e viceversa.
4. Non aggiornare baseline o screenshot per nascondere differenze: una differenza intenzionale si
   revisiona e si approva.
5. Se una modifica tocca i token, aggiorna anche la tavola `docs/design/` quando il valore è
   mostrato.

## Wizard movimento (2026-11-13, implementazione in corso)

| Controllo | Prova eseguita | Esito |
| --- | --- | --- |
| Web — typecheck + build | `cd apps/frontend && npm run lint && npm run build` | **verde** |
| Web — design/contrasti | `check_design.py`, `check_contrast.py` | **verdi** (0 violazioni, 2 divergenze note) |
| Web — wizard | browser demo via CDP, 1440×1100 e 390×844; apertura, passi 1–3, calendario in portal, riepilogo, chiusura con X/`Esc` | **verde**; nessuna baseline visiva aggiunta |
| Web — creazione/eliminazione | `localhost:5173` (CSRF): creato «TEST WIZARD 3» a 12,50 €, notifica «Movimento registrato.», poi eliminato dalla riga | **verde** |
| Web — modifica | apertura da «Modifica», titolo e importo precompilati, passo 1 | **verde** |
| Web — mobile | 390×844: modale a larghezza utile, riepilogo sotto, azioni raggiungibili, nessun overflow orizzontale | **verde** (ispezione) |
| Android — build/test/lint | `source apps/android/build/toolchain/env.sh && cd apps/android && ./gradlew --console=plain :app:assembleDebug :app:testDebugUnitTest :app:lintDebug` | **verde**: BUILD SUCCESSFUL, 31 test, 0 failure, lint 0 errori; APK debug prodotto |
| Android — runtime | device/emulatore | **non eseguito**: wizard non provato a runtime (touch, rotazione, temi, TalkBack); limite dichiarato |

Nota: `design/components.md` e `DESIGN.md` sono **in sola lettura** in questo workspace; i nuovi
componenti `AppSelect`, `DateField`/`TimeField` e la composizione del wizard sono registrati qui e
nelle decisioni, ma non nel catalogo componenti finché il file non torna scrivibile.

Limiti Android dichiarati dal teammate: nessuna prova su device/emulatore; le categorie/tag “recenti”
derivano dalle transazioni caricate (risentono dei filtri); il vecchio `AddMovementDialog` privato
resta nel file `MovementsScreen.kt` ma non è più invocato (codice morto, pulizia successiva).
