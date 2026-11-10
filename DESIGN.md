# Spendy — Design

Identità visiva e sistema di design di **prodotto**: interfaccia web (React/TypeScript) e app
Android (Kotlin/Compose). Documento pubblico, allineato alla release **0.8.3** (10 novembre 2026).
Le decisioni e la progettazione vivono in `.spendy-wiki/` (privata); questo file ne è la
proiezione pubblica e la fonte normativa per l'implementazione.

## Ambito e principi

- **Una sola identità su due piattaforme.** L'app Android è un client nativo a tutti gli effetti:
  stessa palette, stessa tipografia, stesse icone e stesse regole di forma. Material 3 è il
  contenitore, i token Spendy sono il contenuto; nessun colore dinamico Material You.
- **Scuro di default**, chiaro a parità di qualità, più l'opzione **Sistema**.
- **Contrasto AA** su superfici e su fondi semantici; focus sempre visibile; tastiera e touch
  considerati parte del componente, non un'aggiunta.
- **Solo italiano**, EUR, fuso `Europe/Rome`. Nessuna libreria i18n finché non serve una seconda lingua.
- **Gli importi sono neutri**: il colore compare solo su negativi, variazioni e stati.
- **CSS puro + design token** sul web (nessun framework UI); il tema Compose è una **proiezione**
  degli stessi token, non un documento parallelo.
- **Il sistema non è un poster**: token + componenti + stati. `docs/design/` contiene la
  rappresentazione grafica di questo documento e si rigenera dai sorgenti in `docs/design/build/`.

## 01 — Logo

Asset in `apps/frontend/public/logo/` (dettagli in `logo/README.md`). Il simbolo è composto da due
tessere con foro che compongono una **S**, colore primario **`#1DB48B`**; su fondi chiari
**`#166047`**. Colori verificati: 7.31:1 su `#0B0F0D`, 6.96:1 su `#F4F7F5`.

- Lockup **integrato** `[logo]pendy` in orizzontale: il simbolo sostituisce la S iniziale;
  lockup verticale con simbolo sopra e "Spendy" per esteso; lockup solo simbolo.
- Tre varianti senza tagline (orizzontale, verticale, simbolo) in colore su scuro/chiaro e mono
  bianco/nero. Favicon (16/32/48), icone PWA (192/512 + maskable), OG 1200×630, foreground Android.
- **Flat/mono obbligatorio**: il logo deve funzionare senza gradiente né glow, a 16 px e in un solo
  colore. A 16 px la sagoma tiene, i fori sono al limite: per il tassello si usa la favicon dedicata.
- **Gradiente**: ammesso solo negli asset del logo (oggi il pacchetto è piatto). **Glow**: il
  `drop-shadow` è ammesso solo su logo, login ed hero; il glow **ambientale** di pagina (vedi 03)
  è parte dell'identità e non è un effetto del logo.

## 02 — Tema

- **Scuro di default** su web e Android: `#0B0F0D`. Chiaro `#F4F7F5`, a parità di qualità.
- **Tre scelte esplicite**: Scuro, Chiaro, **Sistema** (segue la preferenza del dispositivo).
  Non esiste una modalità "Auto" nascosta: Sistema è una voce dichiarata, con l'icona del monitor.
- **Web**: la preferenza è salvata in `Profile.theme` (`dark`/`light`/`system`, default `dark`) e
  sincronizzata tra dispositivi via API; c'è una cache in `localStorage` per l'avvio e uno script
  di pre-paint che applica il tema risolto prima del primo frame (evita il flash); `theme-color`
  e favicon seguono il tema.
- **Android**: il tema è un'impostazione **locale** (deroga consapevole alla sincronizzazione
  server), default **Sistema**; cambio immediato, nessun riavvio.
- Superfici: `bg0` fondo pagina, `bg1` card e barre, `bg2` campi, liste e stati; `line` per bordi.
- Il **glow ambientale** di pagina è ammesso: due radial-gradient tenui (`--glow1`, `--glow2`)
  sullo sfondo e sull'header, più eventuali aloni d'accento nelle card hero. Non è un effetto del
  logo e non sostituisce il contrasto.

## 03 — Token e forma

I token sono definiti una sola volta in `apps/frontend/src/styles/tokens.css`. Il tema web li
consuma via `var(--…)`; il tema Android li proietta in `Color.kt`/`Theme.kt` con gli stessi valori.

### Superfici e testo

| Token | Scuro | Chiaro | Uso |
| --- | --- | --- | --- |
| `--bg0` | `#0B0F0D` | `#F4F7F5` | fondo pagina |
| `--bg1` | `#111614` | `#FFFFFF` | card, barre, modali |
| `--bg2` | `#18201C` | `#E9EFEC` | campi, liste, stati |
| `--line` | `#26302B` | `#D5DCD7` | bordi e separatori |
| `--text` | `#F4F7F5` | `#0B0F0D` | testo principale (17.89:1) |
| `--muted` | `#9DB3A8` | `#4A5A53` | testo secondario (8.68 / 6.76) |
| `--accent` | `#1DB48B` | `#166047` | accento, link, stati attivi (7.31 / 6.96) |
| `--accent-ink` | `#0B0F0D` | `#FFFFFF` | testo su accento (7.31 / 7.50) |
| `--accent-hover` | `#3FD08C` | `#0D4A34` | hover dell'accento (9.75 / 9.51) |
| `--accent-soft` | `#16241F` | `#E3F2EB` | fondo tenue per badge e stati |
| `--glow1` | `rgb(29 180 139 / .08)` | `#E7F3EC` | alone ambientale mint |
| `--glow2` | `rgb(94 177 239 / .06)` | `#EAF0F8` | alone ambientale blu |

### Semantica

| Token | Scuro | Chiaro | Uso |
| --- | --- | --- | --- |
| `--danger` | `#F26D6D` | `#B53535` | errore, distruttivo (6.60 / 5.52) |
| `--danger-soft` | `#2A1518` | `#F9E3E3` | fondo di errori e badge rifiutati |
| `--warn` | `#E8A33D` | `#8A5604` | attenzione, in attesa (8.95 / 5.70) |
| `--warn-soft` | `#2A2111` | `#F7ECD4` | fondo di avvisi e badge pendenti |
| `--info` | `#5EB1EF` | `#0B6BCB` | informazione (8.28 / 4.89) |
| `--up` | `#3FD08C` | `#166047` | guadagno, entrata (9.75 / 6.96) |
| `--down` | `#F27E7E` | `#C23B3B` | perdita, uscita (7.41 / 4.89) |

**Contrasto sui fondi soft** (testo piccolo, soglia 4.5): scuro danger/danger-soft 5.89,
warn/warn-soft 7.35, accent/accent-soft 6.09; chiaro danger/danger-soft **4.86**,
warn/warn-soft **5.24**, accent/accent-soft 6.49. Sono i valori minimi: non si scende sotto.

### Forma, ombre, movimento

- **Raggio**: `--radius` `18 px` per superfici e controlli (card, campi, bottoni, toast, notice,
  skeleton), `--radius-lg` `20 px` per le modali, `--radius-pill` `999 px` per pillole, badge, switch
  e avatar circolari.
- **Ombre**: una sola elevazione, `--shadow-soft = 0 8px 28px rgb(0 0 0 / .35)` nello scuro e
  `0 8px 28px rgb(11 15 13 / .10)` nel chiaro. Niente ombre multiple o colorate.
- **Movimento**: `--motion-fast 150 ms` (hover, focus, piccoli cambi di stato) e
  `--motion-base 200 ms` (apertura di modali, pannelli, skeleton). Nessuna transizione oltre i 200 ms.
  Ogni animazione rispetta `prefers-reduced-motion` (override globale).
- **Spaziatura**: base 4 px; ritmo 8/12/16/24/32. Contenuto fluido, nessuna larghezza fissa;
  densità maggiore nelle tabelle, respiro nelle pagine. Il ritmo è documentato, ma non è ancora
  tokenizzato: è una convenzione osservata (proposta aperta in `design/decisions.md`).
- **Superfici fisse**: `--overlay` (backdrop delle modali), `--scroll-shadow`, `--accent-glow`
  (alone del logo nell'hero), `--warn-line` (bordo del riquadro in attesa) e `--qr-surface` (sfondo
  del QR, chiaro in entrambi i temi per la scansione) sono token perché valori condivisi, non
  perché semantici.

### Proiezione Android

- Colori: `SpendyBg0/Bg1/Bg2`, `Line`, `Text`, `Muted`, `Accent`, `AccentInk`, `AccentHover`,
  `Danger`, `Warn`, `Info`, `Up`, `Down` in `Color.kt`, per tema scuro e chiaro.
- Forme: `small 18 dp`, `medium 18 dp`, `large 20 dp`; pillole e cerchi come sul web.
- Tipografia: la rampa Compose in `Type.kt` (11–36 sp) usa Inter con gli stessi pesi.

## 04 — Tipografia, cifre e formati

- Font UI: **Inter** self-hosted (`apps/frontend/public/fonts/`, SIL OFL) con quattro pesi:
  **400/500/600/700**. Nessun font esterno, nessun altro peso: niente grassetti sintetizzati.
- Scala web: display `clamp(1.7rem, 3vw, 2.2rem)` / 700 / −0.02em; H2 `1.25rem` / 600;
  body `1rem` / 1.5; label `0.75rem` maiuscolo con +0.14em; importo `1.75rem` / 700;
  secondario `0.92rem`; didascalia `0.78rem`.
- Scala Android: display 36/30 sp, headline 28/24/20 sp, title 18/16/14 sp, body 16/14/12 sp,
  label 14/12/11 sp (tutti SemiBold/Medium/Normal coerenti con i pesi disponibili).
- **Cifre tabulari**: `font-variant-numeric: tabular-nums` su tutta l'interfaccia; la utility
  `.tnum` resta per gli importi in tabelle ed elenchi.
- **Formato importi**: it-IT, EUR, sempre raggruppato, due decimali, spazio insecabile prima di €:
  `1.234,56 €`, `14.853,51 €`, negativi `−24,90 €`. Un solo formattatore per gli importi completi (`format.ts`); le assi dei grafici usano etichette
  compatte con lo stesso locale. Date `gg/mm/aaaa`.

## 05 — Icone e illustrazioni

- **Icone: Lucide**, sia sul web (`lucide-react`) sia su Android (vector drawable derivati da
  Lucide). Tratto 2, terminazioni tonde, 24×24 di base; dimensione 14–24 px secondo il contesto,
  colore `currentColor` (accento per lo stato attivo, `muted` per il resto).
- **Icone canoniche** (fonte: app Android; il web usa le stesse): Dashboard `layout-dashboard`,
  Movimenti `receipt-text`, Conti `wallet`, Salvadanai `piggy-bank`, Automazioni `clock`,
  Investimenti `trending-up`, Categorie e tag `tag`, Cestino `trash-2`, Profilo `user`,
  Impostazioni `settings`, Altro `more-horizontal`; Entrate `arrow-down-left`, Uscite
  `arrow-up-right`. Una destinazione ha una sola icona su entrambe le piattaforme.
- **Illustrazioni: line art mint.** Disegni essenziali a tratto singolo, `stroke-width 2`,
  terminazioni tonde, `viewBox 160×150`, colore accento, dimensioni 96–120 px. Sei soggetti:
  conti, movimenti, salvadanai, investimenti, automazioni, cestino. Sono decorative
  (`aria-hidden`) e accompagnano sempre un titolo.
- **Empty state**: ogni stato vuoto ha illustrazione + titolo + spiegazione breve + azione, quando
  l'azione esiste. Il web le disegna in React con `currentColor`; Android usa gli stessi soggetti
  come vector drawable.

## 06 — Struttura e navigazione

### Web

- **Topbar** sticky e continua, senza linea di stacco: brand lockup theme-swapped a sinistra, sei
  voci icona + etichetta (Dashboard, Movimenti, Conti, Salvadanai, Automazioni, Investimenti;
  per l'admin una sola voce "Amministrazione"), avatar circolare a destra.
- **Menu avatar**: Profilo, Impostazioni, Cestino, Esci (Amministrazione per l'admin). Il menu si
  chiude con Esc, click esterno o quando si sceglie una voce.
- **Footer** con brand testuale e versione (`Spendy · v0.8.1`).
- **Mobile (≤760 px)**: la stessa navigazione diventa **bottom bar fissa** con icone + etichette,
  sfondo con blur e rispetto della safe-area; il contenuto ha padding di compensazione.
- **Dashboard**: selettore periodo a pillole (Mese corrente, Mese precedente, Anno corrente,
  Tutto); card **Saldo del periodo = Entrate − Uscite** (movimenti dei conti: aperture e trasferimenti inclusi) con intervallo,
  eventuali dividendi e quattro metriche (Saldo conti, Salvadanai, Investimenti con valore,
  Patrimonio); card **Grafici del periodo**
  con, nell'ordine, **Andamento saldo e patrimonio** (linea piena = saldo, tratteggio =
  patrimonio), **Entrate vs uscite** (movimenti dei conti: due card con frecce,
  importo e percentuale del totale, una barra segmentata verde/corallo) e **Spese per categoria** (barre orizzontali); sotto, elenchi
  (conti, salvadanai, investimenti) e ultimi 6 movimenti. Su mobile la stessa sequenza in colonna.
- Il periodo **Tutto** parte dalla prima attività reale del profilo, non da una data convenzionale:
  il grafico copre i dati con bucket uniformi (massimo 95 punti, l'ultimo sulla data finale).
- Desktop, tablet e mobile usano lo stesso codice: griglie fluide, nessuna larghezza fissa.

### Android

- **Bottom bar** a cinque voci: Dashboard, Movimenti, Salvadanai, Investimenti, **Altro**;
  "Altro" apre Conti, Automazioni, Cestino, Profilo, Impostazioni. Le **Categorie e tag** si
  aprono dall'icona accanto al titolo della schermata Movimenti. La barra è
  **ancorata al bordo** (60 px + safe area) con superficie piena e una sfumatura di 16 px in
  alto, senza linea di stacco e senza blur. Nessun indicatore:
  la voce attiva è d'accento (icone 20 px, etichette 9,5–10 sp sempre visibili).
- **Dashboard**: stessa sequenza del web — saldo del periodo con quattro metriche, poi
  **Grafici del periodo** (andamento saldo/patrimonio, entrate vs uscite, spese per categoria).
- **Profilo**: avatar a iniziali, nome/email/username, badge stato e ruolo; card «Dati personali»,
  «Accesso» (cambio password) e «Account» con **cambio utente senza reinserire la password**,
  aggiunta di un altro account e uscita. In archivio locale restano solo i dati locali.
- **Impostazioni**: sezioni Accesso, Aspetto (Scuro/Chiaro/Sistema), Blocco screenshot, Dati,
  Aggiornamenti, Informazioni, Dispositivi/QR (solo modalità server).
- **Avatar in alto** con menu rapido, **FAB** globale per aggiungere spesa/entrata/trasferimento,
  **swipe orizzontale** tra le tab, **menu ⋮** per le azioni di contesto (eliminazione in sicurezza).
- **Ricerca globale** dall'alto (server e archivio locale), filtri compatti.
- Layout **adattivo** per smartphone, tablet, foldable e orizzontale; tema Sistema di default;
  blocco screenshot opzionale; biometria/blocco app in modalità locale.

### Pattern di pagina

- **Pagine** per i flussi lunghi e le liste principali; **modali** per conferme e dettagli brevi
  (dettaglio posizione, tassonomia); **CRUD brevi inline** nella pagina (conti, salvadanai,
  automazioni, movimenti).
- **Tabelle** solo dove la densità è informativa (Amministrazione, anteprima import): su mobile
  restano tabelle con **scroll orizzontale** e colonna d'azione affiancata; non c'è conversione a
  card. Le liste principali sono già card/righe.
- **Ricerca**: sul web esiste solo la ricerca interna delle Impostazioni; su Android è globale.
  Nessuna ricerca globale nel web, nessuno switcher di conto nella topbar.

## 07 — Pagine e flussi

| Percorso web | Schermata | Pattern |
| --- | --- | --- |
| `/setup` | Primo avvio (admin) | pagina guidata |
| `/login`, `/register`, `/pending` | Accesso, registrazione, attesa approvazione | pagina + hero con glow |
| `/` | Dashboard | pagina, pill periodo, grafici |
| `/movements` | Movimenti | pagina, form inline, modale tassonomia, filtri |
| `/accounts` | Conti | pagina, form inline |
| `/savings` | Salvadanai | pagina, form inline |
| `/automations` | Automazioni | pagina, form inline, storico |
| `/investments` | Investimenti | pagina, dettaglio in sovrimpressione, archiviate |
| `/import` | Importazione CSV | pagina con anteprima e riepilogo |
| `/trash` | Cestino | pagina con filtri tipo/data |
| `/account` | Profilo | pagina (foto, dati, accesso, password) |
| `/settings` | Impostazioni | pagina con ricerca interna, Aspetto, Dispositivi, Import ed export |
| `/admin` | Amministrazione | pagina di sola lettura (Sistema, backup, release) |
| `*` | 404 | pagina |

Android: onboarding (server/archivio locale), configurazione server e QR, login/registrazione/attesa,
dashboard, movimenti, conti, salvadanai, investimenti, automazioni, cestino, categorie e tag,
notifiche, profilo, impostazioni (Accesso, Aspetto, Dati, Aggiornamenti, Informazioni), dispositivi
e pairing, ricerca.

## 08 — Componenti e stati

Ogni componente ha gli stati **default / hover / focus / disabled / loading / error**; il focus è
sempre un anello di 2 px con offset 2.

- **Bottoni**: primario (accento su `accent-ink`), secondario (bordo `line`, sfondo trasparente),
  ghost (testo accento, hover `accent-soft`), distruttivo (`danger`), link testuale. Altezza
  minima 44 px su touch; il caricamento mostra spinner e mantiene la larghezza.
- **Bottom bar mobile (Android)**: barra ancorata al bordo con superficie piena, cinque voci con
  etichette sempre visibili; la voce attiva è d'accento senza indicatore; una sfumatura di 16 px
  in alto evita lo stacco con il contenuto, che scorre dietro la barra senza essere visibile
  attraverso; i FAB e i contenuti riservano 72 px in fondo.
- **Campi**: label maiuscola, input/select/textarea con `bg2` e bordo `line`, errore con bordo e
  messaggio `danger` sotto il campo. Ricerca con icona e pulsante di pulizia.
- **Card, liste, righe**: sfondo `bg1`, bordo `line`, raggio 18; densità maggiore nelle tabelle.
- **Badge e pillole**: `accent-soft` per gli stati attivi, `warn-soft` per pendenti/in attesa,
  `danger-soft` per rifiutati/disabilitati; raggio 999.
- **Tab e selettori**: tab a pillola con stato attivo `accent-soft`; selettore periodo a pillole.
- **Entrate vs uscite**: due card affiancate (Entrate con `arrow-down-left`, Uscite con
  `arrow-up-right`), importo e percentuale arrotondata del totale; sotto una barra unica
  segmentata con `up` (verde) e `down` (corallo). Identico su web e Android, con totali a zero
  gestiti senza divisioni per zero.
  **Che cosa contano**: sono i **movimenti dei conti**, non dei salvadanai o degli investimenti:
  ogni riga di conto nel periodo conta col suo segno. Quindi rientrano **aperture di conto** e
  **trasferimenti** (anche tra conti dello stesso profilo: generano sia un'uscita sia un'entrata),
  i versamenti/prelievi dai salvadanai e le operazioni sugli investimenti, comprese le righe
  tecniche di ponte. Il **Saldo del periodo è per definizione Entrate − Uscite** e coincide con
  la somma delle variazioni del periodo dei singoli conti; le spese pagate da un salvadanaio
  restano comunque nelle Spese per categoria. L'interfaccia non mostra didascalie
  «inclusi/esclusi»: i tre numeri devono semplicemente quadrare.
- **Grafici**: andamento in SVG artigianale (web) / Canvas (Android), barre in CSS / Compose;
  niente librerie. Legenda ed etichette rendono il significato indipendente dal colore.
- **Menu**: dropdown ancorato all'avatar; voce con icona Lucide, chiusura con Esc/esterno.
- **Modale**: riepilogo delle conseguenze, azione distruttiva a destra, Esc e focus trap, focus
  iniziale su "Annulla", ripristino del focus alla chiusura.
- **Sovrimpressione**: dettaglio posizione e tassonomia in un pannello centrato, stessa semantica
  della modale ma senza conferma.
- **Toast, notice, skeleton, empty state**: vedi 09.
- **Non previsti** (e non da inventare): paginazione, drawer/sheet, tabelle convertite in card,
  ricerca globale web.

## 09 — Feedback e conferme

Due canali distinti, non sovrapposti:

- **Toast** per le azioni puntuali: messaggio, eventuale azione ("Annulla") e chiusura ×; dura 8 s,
  massimo 3 visibili, `aria-live="polite"`. L'annullamento riguarda eliminazioni e ripristini,
  non la retention del cestino.
- **Notice inline** per l'esito dei form: `success` o `warning`, dentro la pagina/sezione.
- **Errori inline** accanto ai campi, con testo esplicito; mai solo colore.
- **Conferma distruttiva** sempre con modale e riepilogo (conto, salvadanaio, posizione, svuota
  cestino, revoca dispositivo, archiviazione).
- **Skeleton** per i caricamenti (blocchi che mantengono il layout, `aria-busy`), non "Caricamento…"
  come unico feedback.
- **Empty state** con illustrazione, titolo, spiegazione e azione quando esiste.
- **Cestino**: soft delete, ripristino, eliminazione definitiva, svuotamento, filtri per tipo e
  data; retention **30 giorni** lato server.

## 10 — Accessibilità

- **Contrasto AA**: testo piccolo ≥ 4.5:1, testo grande e UI ≥ 3:1, sia su `bg0` sia sui fondi
  soft (tabella in 03). I token nascono già dentro la soglia.
- **Focus visibile**: anello di 2 px `accent` con offset 2 su link, bottoni, campi e menu; mai
  `outline: none` senza sostituto.
- **Tastiera**: Esc chiude menu e modali, Tab resta dentro la modale aperta, il focus iniziale è
  sul pulsante sicuro e torna all'elemento che ha aperto la modale.
- **Touch**: aree cliccabili ≥ 44×44 px (icone, chiusura, ricerca, avatar).
- **Grafici mai solo colore**: linea piena/tratteggiata, etichette, percentuali e `aria-label`.
- **Movimento**: transizioni 150–200 ms; `prefers-reduced-motion` disattiva animazioni e scroll
  morbido. Nessun lampeggio.
- **Semantica**: ruoli `dialog`/`status`, `aria-live` per i toast, label esplicite per i campi,
  illustrazioni decorative con `aria-hidden`.

## 11 — i18n e formati

- Solo italiano, senza libreria: stringhe nei componenti, formati in `format.ts` (`it-IT`, EUR).
- Importi `1.234,56 €` (raggruppamento sempre attivo, spazio insecabile), date `gg/mm/aaaa`,
  fuso `Europe/Rome`.
- Quando servirà una seconda lingua, le stringhe si estrarrano da qui; il design non cambia.

## 12 — Governance

- **Fonte dei valori**: `apps/frontend/src/styles/tokens.css` per il web; `Color.kt`, `Theme.kt`,
  `Type.kt` per Android. Ogni nuovo colore, raggio o durata nasce come token e viene proiettato su
  entrambe le piattaforme.
- **Cambiare un token**: aggiornare token web e costante Compose nello stesso commit, verificare i
  contrasti, rigenerare la tavola in `docs/design/`.
- **Gerarchia dei documenti**: `.spendy-wiki/` (privata) decide; questo file è la proiezione
  pubblica e normativa per l'implementazione; `design/` è il livello operativo (catalogo componenti,
  regole di layout, matrice delle piattaforme, verifiche, stato di decisioni e proposte) e non
  duplica i valori; `docs/design/` è la rappresentazione grafica.
- **Manutenzione**: la skill `maintain-design-system` (privata, `.opencode/skills/` + wrapper
  `.dsh/skills/`) e la sua versione pubblica `design/maintenance.md` guidano ogni modifica UI:
  consultare il sistema, riusare token e componenti, aggiornare i documenti nella stessa modifica,
  eseguire `check_contrast.py`, `check_design.py` e la build, dichiarare i controlli non eseguiti.
  Non esiste manutenzione automatica in background.
- **Controlli**: `design/checks/check_design.py` verifica token obbligatori, assenza di colori grezzi
  nei CSS, allineamento dei valori JS/HTML ai token e parità web↔Android (le divergenze note sono
  elencate e non nascoste); il job CI `design-system` esegue questo controllo insieme ai contrasti.
- **Versioning**: questo documento segue la release del prodotto. La sezione "Cronologia" elenca
  ogni allineamento.
- **Cosa non è negoziabile qui**: stack (Django + DRF, React/TypeScript, PostgreSQL, Kotlin +
  Compose), retention del cestino, solo italiano, AA come soglia minima.

## Cronologia

- **0.9.1 — 2026-11-10** — Release 0.8.3: navbar Android «Minimal» ancorata al bordo
  (superficie piena con sfumatura, nessun indicatore), icona profilo per «Altro», Categorie e tag
  in Movimenti, patrimonio grigio nel grafico come sul web; livello operativo `design/` e
  `InlineMessage`; Entrate/Uscite ridefinite come movimenti dei conti (aperture e trasferimenti
  inclusi).
- **0.9 — 2026-11-10** — Release 0.8.2: allineamento design system e correzioni di collaudo: tema Sistema su web e Android; topbar
  continua con avatar e menu; Profilo e Impostazioni separati; Dispositivi e pairing QR; pagine
  Automazioni, Investimenti, Import, Cestino e Admin documentate; app Android inclusa; token unici;
  raggi 18/20 e motion 150/200; pesi 400–700; formato importi raggruppato; contrasti AA sui fondi
  soft; empty state illustrati e skeleton come componenti reali; tabelle con scroll documentate;
  glow ambientale ammesso.
- **0.8 — 2026-11-05** — Prima versione pubblica (Fase O): logo, tema scuro, tipografia, componenti,
  accessibilità.
