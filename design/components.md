# Catalogo componenti

Solo componenti **realmente presenti**, con percorso e uso veri. Il dettaglio visivo normativo è in
`DESIGN.md` §08–09; qui c'è il catalogo operativo per riuso e modifica.

Legenda adozione: **condiviso** = usato da più schermate · **locale** = in una schermata ·
**parziale** = introdotto e usato in alcuni punti, migrazione del resto proposta.

## Componenti React (`apps/frontend/src/components/`)

| Componente | Percorso | Varianti / props | Stati | Adozione |
| --- | --- | --- | --- | --- |
| `Layout` | `Layout.tsx` | shell, topbar con 6 voci + avatar, menu profilo, footer | voce attiva, hover, menu aperto/chiuso, `Esc`, click esterno | condiviso (tutte le pagine autenticate) |
| `SpendyBottomBar` | `ui/components/SpendyBottomBar.kt` | variante «Minimal» (DC-109): 60 dp + inset, senza linea/indicatore, superficie piena con sfumatura di 16 dp in alto (niente blur) | default, press (ripple), focus, selected, swipe col pager | condiviso (MainScreen, 5 tab Android) |
| `AuthHero` | `AuthHero.tsx` | `glow?: boolean`; lockup theme-swapped | dark/light, glow | condiviso (4 usi: login, registrazione, attesa, setup) |
| `Guards` / `LoadingScreen` | `Guards.tsx` | `ProtectedRoute`, `ProfileRoute`, `AdminRoute`, `LoadingScreen` | caricamento, redirect | condiviso (routing) |
| `EmptyState` | `EmptyState.tsx` | `illustration`, `title`, `description?`, `actionLabel?`, `onAction?` | con azione / senza azione | condiviso (9 usi in 6 pagine) |
| `Illustrations` | `Illustrations.tsx` | 6 soggetti: conti, movimenti, salvadanai, investimenti, automazioni, cestino | `currentColor` (accento), `aria-hidden` | condiviso via `EmptyState` |
| `SkeletonLines` | `SkeletonLines.tsx` | `rows`, `variant: lines/cards`, `label` | `role="status"`, blocchi `aria-hidden` | condiviso (cestino, investimenti, dispositivi) |
| `ToastProvider` / `useToast` | `Toast.tsx` | `notify(message, action?)`; max 3 visibili, 8 s, chiusura | azione, annulla, chiusura ×, `aria-live="polite"` | condiviso (7 pagine) |
| `ConfirmModal` | `ConfirmModal.tsx` | `title`, `summary[]`, `confirmLabel`, `busy` | focus iniziale su Annulla, focus trap, `Esc`, busy | condiviso (8 usi in 5 pagine) |
| `InlineMessage` | `InlineMessage.tsx` | `tone: success / warning / error` | notice successo/attenzione, errore di form | **parziale**: introdotto su Profilo (8 usi); il resto usa ancora markup ad hoc |
| `TrendChart` | `Charts.tsx` | `points: SeriesPoint[]` | linea piena saldo, tratteggio patrimonio, legenda | dashboard |
| `InOutBars` | `Charts.tsx` | `income`, `expense` (totali) | percentuali, barra segmentata `up`/`down`, totali a zero | dashboard |
| `CategoryBars` | `Charts.tsx` | `rows: CategoryTotal[]` | barre orizzontali, etichette | dashboard |
| `ImportExportSection` | `ImportExportSection.tsx` | import/export nelle Impostazioni | analisi, anteprima, esito, errore | Impostazioni |
| `DevicesSection` | `DevicesSection.tsx` | dispositivi, pairing QR/codice | caricamento, rinomina, revoca, QR creato/scaduto, errore | Impostazioni |

I componenti sono esportati con nome e usati direttamente dalle pagine; non c'è un barrel file né
un catalogo interattivo (la tavola `docs/design/` è una rappresentazione, non una storybook).

## Primitive CSS (nessun componente React)

Stanno in `apps/frontend/src/styles.css` e si usano con `className`; sono il livello più riusato.

| Primitive | Classi | Varianti / stati |
| --- | --- | --- |
| Bottoni | `button`, `.button`, `.secondary`, `.ghost`, `.danger`, `.small-button`, `.link-button`, `.icon-button` | default, hover, focus-visible, disabled, busy (testo «Salvataggio…») |
| Campi | `input`, `select`, `label`, `.form-field`, `.field-row`, `.checkbox-row`, `.radio-group`, `.file-field`, `.search-clear` | focus/anello, errore, disabled |
| Card e contenitori | `.card`, `.card.narrow`, `.stack`, `.stack-page`, `.two-columns(.equal/.matched)`, `.grid` | densità/colonne responsive |
| Badge e pillole | `.badge`, `.badge.pending`, `.badge.rejected/.disabled`, `.period-segmented`, `.dash-range`, `.theme-choice` | attivo, hover, stati semantici |
| Modali | `.modal-backdrop`, `.modal`, `.modal-wide`, `.modal-close` | aperta, busy, focus trap |
| Tabelle | `table`, `.table-wrap`, `.import-table`, `.position-table` | scroll orizzontale, righe |
| Feedback | `.toast`, `.toast-stack`, `.notice`, `.error`, `.error-text`, `.skeleton`, `.empty-state` | success/warning/errore/caricamento |

Attenzione: `.notice`/`.error` **non** sono più definiti in `styles.css` ma in
`styles/inline-message.css`; per il nuovo codice usare `<InlineMessage>`.

## Markup ad hoc da non imitare (esistente, consolidamento proposto)

| Pattern | Dove (esempi) | Stato |
| --- | --- | --- |
| `<p className="notice success">…</p>` | Admin, Account, Accounts, Savings, Movements, Automations, Investments, Login, Import | esistente; **proposta** di migrazione a `InlineMessage` |
| `<p className="error">…</p>` / `<div className="error">…</div>` | 29 occorrenze in 15 file (Import, Admin, Dashboard, auth, Settings, …) | esistente; proposta di migrazione (attenzione ai `<div>` con contenuto complesso) |
| `.page-heading` + `<h1>` scritto a mano | 9 pagine (Dashboard, Movements, Accounts, Savings, Automations, Investments, Trash, Import) | esistente; un `PageHeading` condiviso è una **proposta**, non una regola |
| `.section-heading` + `<h2>` scritto a mano | Account, Settings, ImportExportSection, DevicesSection | esistente |

## Regole di riuso

1. Cerca prima nel catalogo e con `grep` le classi esistenti: non creare un componente per un solo
   caso senza motivarne l'utilità.
2. Un componente condiviso si modifica considerando **tutti** gli usi elencati qui.
3. Gli stati nuovi (loading, errore, vuoto) si aggiungono al componente, non alla singola pagina.
4. Un componente nuovo entra in questo catalogo nella stessa modifica, con percorso, varianti e
   stato di adozione.
5. Il markup ad hoc non è vietato in assoluto, ma non è il modello da seguire per il nuovo codice.
