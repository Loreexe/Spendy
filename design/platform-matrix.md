# Matrice delle piattaforme

Client effettivamente presenti al 2026-11-11 (release `0.8.4`, **pubblicata**).
Backend e web sono **verificati**; Android è **compilato e testato** (`assembleDebug`, 31 test
unitari, `lintDebug`) ma **non provato su device/emulatore**. Nessun client è inventato: quello che
non esiste è elencato come non previsto.

## Client

| Client | Stato | Tecnologia | Note |
| --- | --- | --- | --- |
| Web desktop | implementato, distribuito | React 19 + TypeScript, CSS puro, Vite | `apps/frontend` |
| Web mobile | implementato | **stessa SPA responsive**, nessun client separato | ≤760 px: bottom bar |
| PWA installabile | manifest presente, **solo online** | `manifest.webmanifest`, icone, theme-color | nessun service worker (DC-096); non funziona offline |
| Android nativo | implementato con limiti (Fase Q + `0.8.4`) | Kotlin + Jetpack Compose, Material 3 + token Spendy | `apps/android`, minSdk 31, versione 0.8.4/versionCode 5; nessuna prova su device in questa sessione |
| iOS / desktop nativo | **non previsto** | — | nessun codice, nessun piano approvato |

Un APK non implica una seconda UI «disegnata a mano»: l'app Android è un client nativo con la stessa
identità, non una copia pixel-per-pixel del web.

## Parti condivise

| Ambito | Condiviso |
| --- | --- |
| Colori, superfici, semantica | token `tokens.css` ↔ costanti `Color.kt`/`Theme.kt` |
| Tipografia | Inter 400/500/600/700, cifre tabulari |
| Icone | set Lucide (web: `lucide-react`; Android: vector drawable) |
| Illustrazioni | 6 soggetti line-art mint (React ↔ vector drawable) |
| Forma | raggi 18/20, pillole 999, ombra singola, motion 150/200 |
| Formati | `it-IT`, EUR, date `gg/mm/aaaa`, ore `HH:MM`, `Europe/Rome` |
| Icone delle categorie | catalogo di 29 icone Lucide condiviso: whitelist backend ↔ `CategoryIcon`/`CategorySelect` web ↔ `CategoryIcons.kt`/drawable Android (0.8.4, DC-117) |
| Feedback | toast/notice/modale con la stessa semantica, skeleton, empty state |

## Differenze intenzionali (approvate o esistenti dichiarate)

| Ambito | Web | Android | Stato |
| --- | --- | --- | --- |
| Navigazione | topbar **6 voci** (Home, Movimenti, Conti, Salvadanai, Automazioni, Investimenti) + menu avatar; bottom bar ≤760 | bottom bar **5 voci** (Home, Movimenti, Salvadanai, Investimenti, Automazioni) + **menu avatar in alto**, barra «Minimal» piena con sfumatura (60 dp), FAB, swipe, ⋮ | implementato 0.8.4 (DC-114): web verificato, Android build/test/lint senza prova device; base 0.8.3 approvata (DC-085/098/102/109) |
| Conti | voce dedicata nella topbar e pagina `/accounts` | **nessuna voce** nella bottom bar: si aprono dal **portafoglio in Home** | implementato 0.8.4 (DC-114): web verificato, Android build/test/lint senza prova device |
| Portafoglio in Home | icona wallet → **popover** con conti, saldi e «Tutti i conti» | icona wallet → **pagina Conti** | implementato 0.8.4 (DC-114): web verificato, Android build/test/lint senza prova device |
| Foto del profilo | foto dal server con fallback iniziali; menu con testata | foto dal server **solo in modalità server**; in archivio locale solo iniziali, nessun upload | implementato 0.8.4 (DC-115): web verificato, Android build/test/lint senza prova device |
| Tema predefinito | Scuro | **Sistema**, impostazione locale | approvato (DC-091/102) |
| Ricerca | solo interna alle Impostazioni | globale (server e archivio locale), voce nel menu avatar | esistente documentato (DESIGN.md §06); non è una regola approvata come vincolo |
| Modalità dati | solo server, online | server **o** archivio locale standalone | approvato (DC-102/104) |
| Blocco screenshot | non previsto | opzionale in modalità locale | approvato (DC-102) |
| Ambito schermate | anche admin/setup | niente admin, setup, gruppi | approvato (DC-102) |
| Blocco app / biometria | non applicabile | biometria obbligatoria in locale, blocco opzionale in server | approvato (DC-102) |

Queste differenze sono adattamenti, non incoerenze. **Una differenza non elencata qui è
un'eccezione da approvare** (procedura in [`decisions.md`](./decisions.md)).

## Divergenze tecniche note (aperte)

- **Palette chiara**: i token web `--danger`/`--warn` del tema chiaro sono stati cambiati nella
  release 0.8.2 (AA sui fondi soft, vedi `DESIGN.md` §03), ma `Color.kt` usa ancora i valori della
  palette approvata in DC-090. Il `check_design.py` la segnala come divergenza nota: serve una
  decisione (allineare Android o registrare la differenza).
- **Proiezione Android incompleta**: `warn-soft`, `accent-hover`, `accent-ink`, aloni e `--overlay`
  non hanno un equivalente Compose; i componenti Android usano `MaterialTheme` o derivazioni
  locali. Non è un problema finché i valori derivati restano coerenti, ma va documentato quando un
  componente Android usa un colore nuovo.
- **PWA**: senza service worker l'installazione è solo una scorciatoia, non un'app offline. Non
  dichiarare funzionamento offline.
- **Archivi personali**: il backend è allo **schema 5** (ora e icone) dalla `0.8.4`,
  mentre l'archivio locale Android ha un formato proprio (schema 2, con import dello schema 1): non
  esiste parità formale tra i due archivi. Va dichiarato quando si parla di migrazione.
- **Orario e Room**: sul web l'ora arriva dall'API; su Android la migrazione **Room 6→7** aggiunge
  `time` (default 12:00) e `icon` (default `tag`) e il DTO usa il fallback 12:00 con server `0.8.3`.
  La migrazione è compilata e coperta dai test unitari, ma **non è verificata a runtime su device**.

## Verifiche per piattaforma

| Piattaforma | Verifica reale possibile | Cosa non dimostra |
| --- | --- | --- |
| Web | `tsc` + build, controlli statici, ispezione a 390/1440 px, temi | nulla sul client nativo |
| Android | `assembleDebug`, test unitari, `lintDebug` (comandi CI) | non sostituiscono una prova su emulatore/dispositivo |
| PWA | manifest e icone ispezionabili; prova installazione manuale | non verifica offline (non previsto) |

Non dichiarare verificato su Android ciò che è stato provato solo nel browser.
