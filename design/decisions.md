# Decisioni e stato del design system

Registro del livello operativo. Le decisioni **approvate** vivono in `.spendy-wiki/DECISIONS.md`
(privata) e sono qui riportate per riferimento; le incoerenze osservate **non** sono decisioni.

Legenda: **Approvato** = scelta esplicita dell'utente · **Osservato** = presente nel codice ma non
approvato come regola · **Proposto** = raccomandazione in attesa di approvazione · **Deprecato** =
non usare per nuovo codice (serve approvazione per dichiararlo tale).

## Decisioni approvate rilevanti

| Decisione | Contenuto | Impatto sul design system |
| --- | --- | --- |
| DC-084 | identità visiva e logo Spendy (flat/mono, tre lockup, pacchetto asset) | logo, favicon/PWA/OG; `DESIGN.md` §01 |
| DC-085 | design system, tema scuro di default, AA, forma 18–20 px, CSS puro + token, topbar desktop/bottom bar mobile, feedback, motion 150–200 ms, Lucide, line-art, empty state con azione | fondamenta del sistema; `DESIGN.md` §02–11 |
| DC-090 | Inter self-hosted, palette AA, `tokens.css` come unico file di token | fonte autorevole dei token |
| DC-091 | preferenza tema nel profilo e sincronizzazione web; nessuna libreria i18n (solo italiano, formati centralizzati) | `theme.ts`, `format.ts`, tema chiaro/scuro |
| DC-092 | shell, tema scuro applicato, topbar/bottom bar, componenti base migrati ai token | `Layout.tsx`, `styles.css` |
| DC-096 | QA e PWA: manifest + icone, nessun service worker (solo online), `DESIGN.md` pubblico | `manifest.webmanifest`, limiti PWA |
| DC-098 | topbar continua con avatar e menu, Profilo/Impostazioni separati, niente didascalie | `Layout.tsx`, `AccountPage`, `SettingsPage` |
| DC-102 | Android Kotlin + Compose, Material 3 con token Spendy, bottom bar 5 voci, tema Sistema locale, solo italiano | `apps/android`, `platform-matrix.md` |
| DC-109 | navbar mobile Android «Minimal»: ancorata 60 dp, nessuna linea/indicatore, superficie piena con sfumatura di 16 dp in alto (niente blur, rivista su richiesta); Compose resta 1.7.6 | `ui/components/SpendyBottomBar.kt`, `MainScreen.kt`; `DESIGN.md` §06/§08 |
| DC-114 | Home e navigazione: Home (icona `house`) al posto di Dashboard, topbar web a 6 voci, bottom bar Android a 5 voci senza «Altro», Conti dal portafoglio, Home con azioni rapide, popover conti, ultimi 3 movimenti e tre card separate, menu avatar con testata e voci | **implementato e verificato** (2026-11-11): web verificato con build, controlli e ispezione visiva 390/1440 px nei due temi; Android compilato e testato (31 test, lint), **senza prova su device**; `DESIGN.md` §05/§06/§08, catalogo e layout |
| DC-115 | Profilo, avatar e foto: foto del profilo su web e Android con fallback iniziali, upload Android solo in modalità server, testata del menu con foto/nome/cognome/email | **implementato e verificato** (2026-11-11): web verificato (foto profilo e testata del menu); Android compilato e testato, upload/rimozione non provati su device |
| DC-116 | Orario dei movimenti: `time` con default 12:00, API `HH:MM`, POST opzionale (ora corrente `Europe/Rome`), migrazione, CSV a 6 colonne, archivio schema 5, Room v7 | **implementato e verificato** (2026-11-11): backend 383 test e API provata dal vivo; web verificato; Android compilato e testato, migrazione Room non provata a runtime |
| DC-117 | Icone delle categorie: `Category.icon` con whitelist di 29 icone Lucide, mappatura delle 9 predefinite, catalogo extra, «Altro» con icona modificabile | **implementato e verificato** (2026-11-11): backend 383 test e API provata dal vivo; web verificato; Android compilato e testato, resa non provata su device |
| DC-103/104 | API v1 per il client nativo; archivio locale standalone e migrazione | differenza web/Android sulla modalità dati |
| DC-105/106 | distribuzione APK, verifiche e fasi della Fase Q | stato «Android implementato con limiti» |

## Convenzioni osservate (esistenti, non approvate)

1. `tokens.css` è l'unico file con valori di colore; i CSS dei componenti condivisi stanno in
   `styles/*.css` (`empty-state.css`, `inline-message.css`) importati da `main.tsx`.
2. Primitive CSS piatte (`.card`, `.button.secondary`, `.badge.pending`, …) riusate nelle pagine.
3. Scala tipografica e spaziature applicate con valori letterali, non con token dedicati.
4. Feedback inline scritto a mano (`<p className="notice…">` / `<p className="error">`) accanto ai
   componenti condivisi `Toast` e `ConfirmModal`.
5. `docs/design/build/` è la pipeline dati→tavola (HTML autonomo, poster, verifica contrasti).
6. Nessun test frontend né baseline visiva: le verifiche sono build, controlli statici e ispezione.

## Incoerenze osservate (aperte, non standard)

| # | Incoerenza | Evidenza | Effetto |
| --- | --- | --- | --- |
| 1 | palette chiara `--danger`/`--warn` cambiata dal 0.8.2 senza una DC dedicata | `tokens.css` `#b53535`/`#8a5604`; DC-090 approvava `#C23B3B`/`#9A6206`; `DESIGN.md` 0.9 documenta i nuovi valori; `Color.kt` usa ancora quelli DC-090 | web e Android divergono sul tema chiaro; il `check_design.py` la segnala come divergenza nota |
| 2 | tabelle su mobile: DC-085 prevedeva «tabelle→card» | implementazione e `DESIGN.md` §06 documentano tabelle con **scroll orizzontale** | divergenza tra decisione e realtà: da registrare o correggere |
| 3 | markup inline duplicato (`notice`/`error`) | 15+ file; `InlineMessage` introdotto solo sul Profilo | costo di manutenzione e stati incoerenti |
| 4 | `.page-heading`/`.section-heading` scritti a mano in 9+ pagine | `grep` su `pages/` | struttura ripetuta senza componente |
| 5 | proiezione Android incompleta (`warn-soft`, `accent-hover`, `accent-ink`, aloni, overlay) | `Color.kt`/`Theme.kt` | possibili derivazioni locali non tracciate |
| 6 | spaziature non tokenizzate | valori `rem` letterali nel CSS | nessun controllo automatico sul ritmo 4/8/12/16/24/32 |

## Proposte (in attesa di approvazione)

| # | Proposta | Perché | Impatto / approvazione |
| --- | --- | --- | --- |
| P-1 | registrare in una DC la palette chiara attuale e **allineare `Color.kt`** (`danger`, `warn`) a `tokens.css` | chiudere la divergenza web/Android con una fonte unica | cambia leggermente due colori Android; richiede approvazione e prova su dispositivo |
| P-2 | completare la migrazione a `InlineMessage` in tutte le pagine, inclusi gli errori di form | markup unico, stati coerenti | refactor meccanico senza cambio visivo; da fare in una modifica dedicata con build verde |
| P-3 | introdurre un componente `PageHeading`/`SectionHeading` condiviso | elimina la ripetizione in 9+ pagine | estensione compatibile; richiede approvazione perché tocca molte schermate |
| P-4 | introdurre token di spaziatura (`--space-*` sul ritmo 4/8/12/16/24/32) e migrare i valori | rendere il ritmo verificabile | migrazione estesa: approvazione esplicita |
| P-5 | infrastruttura di test frontend e baseline visive (es. Vitest + Playwright) | oggi non c'è alcun test UI automatico | **nuove dipendenze**: approvazione esplicita prima di installare |
| P-6 | completare la proiezione Android dei token mancanti | parità verificabile anche su Compose | da valutare per componente; nessuna urgenza |
| P-7 | service worker per la PWA offline | — | **non proposto**: DC-008/096 prevedono solo online |
| P-8 | navbar mobile Android: tre varianti valutate (01 Bolla, 02 Pillola, 03 Barretta) in `docs/design/navbar-preview.html` | riferimento esterno rivisto con i token Spendy | **ritirata**: la 01 è stata implementata e rifiutata in collaudo (bolla troppo grande, barra staccata, icona tagliata); codice ripristinato. Nuovo prototipo M3-style in valutazione (P-9) |
| P-9 | navbar mobile Android in stile **Material 3** (barra agganciata 80 + inset, indicatore a pillola, etichette 12 sp): prototipo in `docs/design/navbar-m3-preview.html` | risposta al rifiuto della «Bolla» | **ritirata in collaudo**: non gradita all'utente; sostituita dal laboratorio di cinque prototipi (P-10) |
| P-10 | **cinque prototipi navbar** agganciati al bordo (Linea, Blocco, Cerchio, Segmenti, Minimal in vetro) in `docs/design/navbar-lab-preview.html` | risposta al rifiuto di «Bolla» e M3 | **approvata come DC-109**: scelta la 05 «Minimal» in vetro; implementata; prova su device ancora da fare (telefono scollegato durante l'installazione) |

P-8 è stata implementata come DC-108 e poi **ritirata**: la variante 01 «Bolla» non è piaciuta in prova sul dispositivo (bolla troppo grande e rialzata, barra flottante staccata dal resto, spazio vuoto, icona tagliata durante il sollevamento). Il codice è ripristinato alla `NavigationBar` Material 3 e il dispositivo è tornato all'APK ufficiale `0.8.2`. La preview locale `docs/design/navbar-preview.html` resta come memoria delle varianti scartate. **P-9** (Material 3) è stato **ritirato in collaudo** su richiesta dell'utente. **P-10** è stato **approvato come DC-109**: la variante 05 «Minimal» è implementata (senza blur, dopo revisione); le altre quattro proposte restano documentate nella preview locale.

## Deprecati

Nessun elemento è stato approvato come deprecato. Candidati da valutare (richiedono approvazione):

- markup `<p className="notice…">` / `<p className="error">` scritto a mano al posto di
  `InlineMessage` (dopo la migrazione completa);
- `.page-heading`/`.section-heading` scritti a mano al posto del futuro componente condiviso.

## Procedura per nuove varianti ed eccezioni

1. **Classifica**: uso esistente · estensione compatibile · nuova variante · eccezione di
   piattaforma · nuova decisione.
2. **Verifica** se un componente/token esistente risolve già il caso; documenta perché non basta.
3. **Proponi** all'utente con 1–3 alternative, impatto visivo, costo e verifiche possibili. Non
   approvare da solo.
4. **Se approvato**: registra la decisione in `.spendy-wiki/DECISIONS.md` (`DC-*`), aggiorna
   `DESIGN.md` se cambia l'identità e questo file; per un'eccezione di piattaforma aggiorna
   `platform-matrix.md`.
5. **Implementa** con token/componenti riusati, aggiorna catalogo e verifiche nella stessa modifica.
6. **Se non approvato**: resta `Proposto` qui; non entra nel codice come regola implicita.

## Nota sul versionamento

`DESIGN.md` **0.9.2** (2026-11-11), release di prodotto 0.8.4 (DC-114…117), descrive: Home e navigazione,
foto/avatar e menu, orario dei movimenti, icone delle categorie. Backend e web sono verificati;
Android è compilato e testato ma non provato su device. Le modifiche del
livello operativo (catalogo, regole, controlli, consolidamenti di token senza cambio visivo) **non**
cambiano la versione dell'identità; cambiano solo quando cambia un valore visivo approvato.
