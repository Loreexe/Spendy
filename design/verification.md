# Verifiche

Controlli **esistenti** e realmente eseguibili. Non tutti sono automatici: quelli manuali vanno
dichiarati come tali. Lo stato riportato è l'ultima esecuzione conosciuta, non una promessa.

## Comandi

| Controllo | Comando | Verifica | Stato 2026-11-10 |
| --- | --- | --- | --- |
| Typecheck + build web | `cd apps/frontend && npm run lint && npm run build` | TypeScript e bundle di produzione | **verde** (2.115 moduli, build ~2 s) |
| Contrasti AA token | `python3 docs/design/build/check_contrast.py` | 12 coppie testo/sfondo x 2 temi ≥ 4.5:1 | **verde** (tutte AA) |
| Controlli design system | `python3 design/checks/check_design.py` | token obbligatori, colori grezzi nei CSS, mirror JS/HTML, parità web↔Android, raggi, durate | **verde** (0 violazioni, 2 divergenze note documentate) |
| Versione allineata | `python3 scripts/check_version.py` (+ test dello script) | `VERSION` = package/Android | non rieseguito qui (nessuna modifica di versione) |
| Backend | `cd apps/backend && python manage.py test` | suite Django (richiede PostgreSQL) | non eseguito qui (nessuna modifica backend) |
| Android build/test/lint | `cd apps/android && ./gradlew :app:assembleDebug :app:assembleRelease :app:testDebugUnitTest :app:lintDebug` | compilazione Compose, test unitari, lint, APK release firmato | **verde** (2026-11-10, DC-109: assembleDebug/Release, 18 test, lint 0 errori; APK firmato installato sul telefono) |
| Tavola grafica | `python3 docs/design/build/build_html.py` + cattura CDP (`docs/design/README.md`) | rigenerazione della rappresentazione | non necessario: nessun valore visivo cambiato |
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

## Navbar «Minimal» (2026-11-10, DC-109)

- **Implementazione**: `ui/components/SpendyBottomBar.kt` (barra 60 dp + inset, senza linea/indicatore, etichette sempre visibili) con superficie piena e sfumatura di 16 dp in alto; `MainScreen` è passato da `Scaffold` a top bar + pager a tutta altezza + barra in overlay, con `LocalBottomBarInset` (72 dp) per contenuti e FAB.
- **Revisione**: il primo giro usava il blur reale (`rememberGraphicsLayer` + `BlurEffect`) con Compose 1.8.3; l'utente ha chiesto di toglierlo perché non gradito. Blur rimosso, superficie piena, Compose BOM riportato a **Compose 1.7.6** (BOM 2024.12.01).
- **Verifiche eseguite**: `assembleDebug` e `assembleRelease` verdi; 18 test unitari; `lintDebug` 0 errori; APK release firmato e **installato in place** sul telefono (`install -r`, `versionName 0.8.2`, dati conservati).
- **Verifica a schermo**: barra ancorata senza linea e senza blur, sfumatura in alto, tab Dashboard e Movimenti funzionanti, FAB sollevato sopra la barra, scorrimento del contenuto. **Non verificati**: TalkBack, scala del testo, tema chiaro e tablet/foldable.
- La preview locale della variante è `docs/design/navbar-lab-preview.html` (non tracciata), non è una verifica del client nativo.

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
| Accessibilità | contrasto, etichette, ruoli (`dialog`, `status`), illustrazioni `aria-hidden`, target ≥ 44 px |
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
