# Regole di layout e navigazione

Fonte normativa: `DESIGN.md` §06. Qui le regole operative verificate sul codice reale
(`apps/frontend/src/styles.css`, `Layout.tsx`, `App.tsx`).

## Shell web

| Elemento | Regola reale | Note |
| --- | --- | --- |
| `.app-shell` | colonna, `min-height: 100vh` | footer in fondo anche con poco contenuto |
| `.app-header` | sticky in alto, sfondo `--page-background` fisso, padding `0.85rem clamp(1rem, 4vw, 2.5rem)` | nessuna linea di stacco (DC-098) |
| `.app-nav` | barra orizzontale centrata, 6 voci icona + etichetta | admin: una sola voce «Amministrazione» |
| avatar + menu | a destra, dropdown di Profilo, Impostazioni, Cestino, Esci | `Esc`, click esterno, chiusura alla scelta |
| `.app-main` | `max-width: 1080px`, centrato, padding `clamp(1.5rem, 4vw, 3rem) clamp(1rem, 4vw, 2rem)` | nessuna larghezza fissa di pagina |
| `.app-footer` | brand + versione, bordo superiore | |

## Breakpoint effettivi

Nel CSS esistono **due** breakpoint, non una scala arbitraria:

| Breakpoint | Uso |
| --- | --- |
| `max-width: 900px` | dashboard: `.stat-grid` a 2 colonne, `.dash-summary`/`.dash-charts-row` a 1 colonna, `.dash-breakdown` a 2 |
| `max-width: 760px` | **mobile**: topbar → bottom bar fissa, griglie a 1 colonna, righe entità in colonna, padding inferiore `5.5rem` per la barra |

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
- **Dashboard**: pill periodo → riepilogo con 4 metriche → grafici (andamento, entrate vs uscite,
  categorie) → elenchi e ultimi movimenti. Su mobile la stessa sequenza in colonna.
- **Impostazioni/Profilo**: blocchi `.settings-block` / sezioni `.profile-section` con
  `.section-heading` e form `.stack`; nessuna didascalia esplicativa.
- **Auth/setup**: `.card.narrow` (max 420 px) centrata con `AuthHero` e glow.

## Adattamenti Android (intenzionali)

- Bottom bar a 5 voci (Dashboard, Movimenti, Salvadanai, Investimenti, Altro); «Altro» apre il resto. Barra «Minimal» (DC-109): ancorata, 60 dp + inset, nessuna linea/indicatore, superficie piena con sfumatura di 16 dp in alto (niente blur); contenuti scrollabili riservano 72 dp e i FAB sono sollevati.
- FAB globale per aggiunta rapida; avatar in alto con menu; swipe tra le tab; menu ⋮ per azioni.
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
