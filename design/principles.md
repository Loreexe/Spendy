# Princìpi — Spendy

Riferimento normativo: [`DESIGN.md`](../DESIGN.md) § «Ambito e principi» e § 01–11. Qui si trovano
solo i princìpi **operativi** che guidano le decisioni quotidiane, con lo stato reale.

## Identità (approvata, DC-084/085/090/102)

- **Una sola identità su web e Android.** Stessa palette, Inter, Lucide, illustrazioni line-art,
  stessi raggi e stessa semantica di colore. Material 3 è il contenitore Android, non una seconda
  identità; nessun colore dinamico Material You.
- **Scuro di default** sul web; **Sistema** di default su Android (deroga locale approvata, DC-102).
  Il chiaro è a parità di qualità, non un ripensamento.
- **AA come soglia minima** su superfici e fondi soft; focus sempre visibile; tastiera e touch
  fanno parte del componente.
- **Gli importi sono neutri**: il colore compare solo su negativi, variazioni e stati.
- **CSS puro + design token** sul web, nessun framework UI. Il tema Compose è una proiezione dei
  token, non un documento parallelo.
- **Solo italiano**, EUR, `Europe/Rome`, nessuna libreria i18n finché non serve una seconda lingua.

## Interazione (approvata)

- **Due canali di feedback distinti, mai sovrapposti**: toast per l'azione puntuale (max 3, 8 s,
  `aria-live`), messaggio inline per l'esito di form/sezione e per gli errori.
- **Conferma distruttiva sempre** con modale e riepilogo delle conseguenze; focus iniziale
  sull'azione sicura, `Esc` chiude, focus trap, ritorno del focus alla chiusura.
- **Stati pertinenti per ogni componente**: normale, hover (dove c'è puntatore), focus visibile,
  disabilitato, caricamento, errore, vuoto, successo.
- **Caricamento con skeleton** che mantengono il layout (`aria-busy`), non «Caricamento…» come unico
  segnale; **empty state** con illustrazione, titolo, spiegazione e azione quando esiste.
- **Movimento 150–200 ms**, nessuna transizione più lunga, `prefers-reduced-motion` rispettato.
- **Niente didascalie o spiegazioni di regole nelle pagine** (DC-098): restano avvisi, errori e
  stati vuoti.

## Convenzioni osservate (esistenti, non approvate come regola)

- Un solo file di token (`styles/tokens.css`); i CSS dei componenti condivisi vivono in
  `styles/*.css` (`empty-state.css`, `inline-message.css`) e vengono importati in `main.tsx`.
- Classi CSS piatte (`.card`, `.button.secondary`, `.badge.pending`, …) riusate nelle pagine; non
  esiste un sistema di utility class.
- La spaziatura è un **ritmo documentato** (base 4 px: 8/12/16/24/32) applicato con valori `rem`
  letterali: non è ancora tokenizzata (vedi proposte in [`decisions.md`](./decisions.md)).
- Le stringhe sono inline nei componenti; i formati passano da `format.ts`.

## Adattamenti intenzionali (non incoerenze)

- **Navigazione**: topbar su web, bottom bar su mobile e su Android; la destinazione è la stessa,
  cambia il contenitore (DESIGN.md §06, DC-085/102).
- **Ricerca**: sul web esiste solo la ricerca interna delle Impostazioni; su Android è globale.
- **Tema**: default scuro sul web; su Android il tema è locale e il default è Sistema.
- **Modalità offline**: Android ha l'archivio locale standalone; il web è solo online (DC-008/104).
- **Densità**: tabelle informative restano tabelle con scroll orizzontale anche su mobile; le liste
  principali sono già righe/card e non vengono convertite.

Ogni altra differenza tra piattaforme è un'eccezione da documentare in
[`platform-matrix.md`](./platform-matrix.md) e da approvare.

## Non obiettivi

- Identità pixel-per-pixel tra web e Android.
- Un nuovo framework UI, una seconda libreria di icone, un secondo font.
- Colori dinamici Material You, temi aggiuntivi oltre scuro/chiaro/Sistema.
- Un design system parallelo a `DESIGN.md`: `design/` non contiene valori, solo regole e stato.
