# Regole di layout e navigazione

Fonte normativa: `DESIGN.md` §06. Qui le regole operative verificate sul codice reale
(`apps/frontend/src/styles.css`, `Layout.tsx`, `App.tsx`).

> **Aggiornamento 2026-11-12 — rifiniture Home (non rilasciate):** toolbar mobile impilata, importi firmati, stati vuoto/caricamento/errore accessibili, grafico leggibile a 390 px. Vedi la sezione «Home e portafoglio».
>
> **Aggiornamento 2026-11-11 — release `0.8.4` (DC-114…117):** le parti contrassegnate «0.8.4»
> sono **implementate e verificate sul web** (ispezione visiva 390/1440 px nei due temi); su Android
> sono **compilate e testate** (`assembleDebug`, 31 test unitari, `lintDebug`) ma **non provate su
> device/emulatore**. Le regole senza etichetta descrivono la base consolidata.

## Shell web

| Elemento | Regola reale | Note |
| --- | --- | --- |
| `.app-shell` | colonna, `min-height: 100vh` | footer in fondo anche con poco contenuto |
| `.app-header` | sticky in alto, sfondo `--page-background` fisso, padding `0.85rem clamp(1rem, 4vw, 2.5rem)` | nessuna linea di stacco (DC-098) |
| `.app-nav` | barra orizzontale centrata, 6 voci icona + etichetta; admin: una sola voce «Amministrazione». 0.8.4: la prima voce è **Home** (icona `house`), poi Movimenti, Conti, Salvadanai, Automazioni, Investimenti | voce attiva evidenziata |
| avatar + menu | a destra, dropdown con voci Profilo, Impostazioni, Cestino, Esci. 0.8.4: **testata** con foto/nome/cognome/email e voci Profilo, Impostazioni, **Import/Export**, Cestino, Esci (admin: Profilo, Impostazioni, Amministrazione, Esci) | `Esc`, click esterno, chiusura alla scelta |
| `.app-main` | `max-width: 1080px`, centrato, padding `clamp(1.5rem, 4vw, 3rem) clamp(1rem, 4vw, 2rem)` | nessuna larghezza fissa di pagina |
| `.app-footer` | brand + versione, bordo superiore | |

## Breakpoint effettivi

Nel CSS esistono **due** breakpoint, non una scala arbitraria:

| Breakpoint | Uso |
| --- | --- |
| `max-width: 900px` | dashboard: `.stat-grid` a 2 colonne, `.dash-summary`/`.dash-charts-row` a 1 colonna, `.dash-breakdown` a 2 |
| `max-width: 760px` | **mobile**: topbar → bottom bar fissa, griglie a 1 colonna, righe entità in colonna, padding inferiore `5.5rem` per la barra; Home: toolbar periodo/date impilata, pill a capo (attivo `accent-soft`), target ≥44 px |

Regole:

- Sotto 760 px la navigazione diventa `.app-nav` **fissa in basso**, con blur, `env(safe-area-inset-bottom)`
  e icone + etichette compatte; il contenuto riceve padding di compensazione.
- Non introdurre nuovi breakpoint per una singola schermata: se serve, aggiorna questo file e
  `platform-matrix.md` e proponi la modifica.
- Le griglie usano `minmax(0, 1fr)` e `flex-wrap`; nessuna altezza fissa di card o pagina.
- Tabelle informative: `.table-wrap` con scroll orizzontale anche su mobile; non diventano card.

## Pattern di pagina (approvati)

- **Pagina** per flussi lunghi e liste principali; **modale** per conferme e dettagli brevi;
  **CRUD inline** nella pagina per conti, salvadanai, automazioni, movimenti.
- **Wizard movimento (2026-11-13, approvato via preview e implementato web):** la pagina Movimenti apre un
  `+ Nuovo movimento` / modifica in una **modale a 3 passi** (Importo → Dettagli → Conferma) con
  **riepilogo laterale sempre visibile** su desktop; a ≤760 px la modale occupa la larghezza utile,
  il riepilogo va sotto il contenuto e le azioni restano raggiungibili; a ≤900 px il riepilogo passa
  sotto. Il passo 1 include pillola tipo, importo digitabile con ± e slider a tacche 0–100 € (0,50 €),
  conti con listbox app-style e due selettori Da/A per i trasferimenti; il passo 2 descrizione,
  categoria con icone e pillole recenti; il passo 3 data/ora con mini calendario e mini orologio,
  tag recenti e **Conferma**. Su Android il flusso è a **4 passi** con riepilogo finale (vedi
  `platform-matrix.md`).
- **Home (web)**: pill periodo → riepilogo con 4 metriche e portafoglio → card «Grafici del periodo» (andamento, entrate vs uscite e categorie) → elenchi Conti/Salvadanai → ultimi 4 movimenti compatti (icona categoria a sinistra, icona del tipo accanto all'importo, senza righe contabili). Su mobile la stessa sequenza in colonna. Modifica successiva alla `0.8.4` (non rilasciata): rimossi i tasti `+ Movimento`/`Trasferimento` e ripristinato il resto della Home precedente, mantenendo la prima card con il portafoglio.
- **Skeleton di pagina (2026-11-12, non rilasciato)**: ogni route usa lo skeleton della propria forma (`components/PageSkeletons.tsx`, `RouteSkeleton` per il fallback setup/auth): heading reale, card e righe corrispondenti alla pagina; Home ha `HomeSkeleton` completa. La vecchia card centrata di `LoadingScreen` non è più usata dai guard né dalle pagine principali.
- **Home — rifiniture 2026-11-12 (non rilasciate)**: a ≤760 px la toolbar va a capo (niente scroll orizzontale), i target salgono a ≥44 px; gli importi dei movimenti sono firmati e colorati per direzione (spese «−»/`--down`, entrate «+»/`--up`, trasferimenti neutri) come su Android; le righe compatte restano su una linea con titolo troncato; i grafici sono nascosti quando non hanno dati; le liste vuote usano `EmptyState` con CTA; caricamento con skeleton che riproduce la struttura delle card reali (hero, grafici, elenchi, movimenti) e `aria-busy`, mostrato **dalla prima pittura** anche durante setup/auth (fallback di route al posto della card centrata), aggiornamento con stato live, errore con `role="alert"`, «Riprova» e nota sui dati non aggiornati; etichette del grafico Andamento con corpo reso ≥11 px. La card Conti mostra la nota «Saldo del periodo; tra parentesi il saldo attuale con i salvadanai» e «Saldo conti» resta neutro.
- **Impostazioni/Profilo**: blocchi `.settings-block` / sezioni `.profile-section` con
  `.section-heading` e form `.stack`; nessuna didascalia esplicativa.
- **Auth/setup**: `.card.narrow` (max 420 px) centrata con `AuthHero` e glow.

## Home e portafoglio (0.8.4, implementato)

Ordine dei contenuti della Home (web e Android hanno contenitori diversi):

**Web** (modifica successiva alla `0.8.4`, non rilasciata):
1. **Eyebrow «Home»** e selettore periodo a pillole.
2. **Card saldo del periodo** con quattro metriche e **icona wallet in alto a destra**.
3. **Card «Grafici del periodo»** con Andamento saldo/patrimonio, poi Entrate vs uscite e Spese
   per categoria affiancate.
4. **Elenchi Conti e Salvadanai** in due colonne, con «Gestisci».
5. **Ultimi 4 movimenti compatti**: data, ora, categoria e icona del tipo; nessuna riga contabile, icona categoria più grande a sinistra.
6. Niente azioni rapide in Home.

**Android** (0.8.4, invariata): card saldo → azioni rapide `+ Movimento`/`Trasferimento` (dialogo
Movimenti col tipo già scelto) → ultimi 3 movimenti → tre card separate (Entrate vs uscite,
Andamento, Spese per categoria).

**Popover del portafoglio** (`AccountsMenu`, solo web): ancorato all'icona wallet della card saldo,
elenca i conti con il saldo e la voce «Tutti i conti»; si chiude con `Esc`, click esterno o scelta;
focus visibile e target ≥ 44 px; non è una pagina e non duplica la destinazione «Conti» della
topbar. Su Android il portafoglio apre direttamente la **pagina Conti**.

## Adattamenti Android (intenzionali)

- Bottom bar a 5 voci (Dashboard, Movimenti, Salvadanai, Investimenti, Altro); «Altro» apre il resto. Barra «Minimal» (DC-109): ancorata, 60 dp + inset, nessuna linea/indicatore, superficie piena con sfumatura di 16 dp in alto (niente blur); contenuti scrollabili riservano 72 dp e i FAB sono sollevati. **0.8.4 (DC-114):** voci **Home, Movimenti, Salvadanai, Investimenti, Automazioni**; «Altro» rimosso e Conti dal portafoglio.
- FAB globale per aggiunta rapida; **top bar con avatar a destra e menu** (testata foto/nome/cognome/email; Profilo, Impostazioni, Import/Export, Cestino, Ricerca, Esci); swipe tra le tab; menu ⋮ per azioni.
- Layout adattivo per smartphone/tablet/foldable e orizzontale; Material 3 è il contenitore.
- Dettagli e limiti in `platform-matrix.md`; non replicare pattern desktop sul telefono.

## Regole di modifica

1. Una nuova schermata usa la shell esistente (`Layout`) e le classi di pagina esistenti.
2. Nuovi layout a griglia preferiscono `.grid`, `.two-columns`, `.stack-page`; non introdurre
   griglie monouso se una classe esistente basta.
3. Ogni regola responsive nuova va motivata e verificata a 390 px e 1440 px (vedi
   [`verification.md`](./verification.md)).
4. Il focus da tastiera deve restare visibile e raggiungibile in ogni breakpoint; la bottom bar non
   copre controlli o toast.
5. Nessun contenuto essenziale solo in hover: il touch non ha hover.
