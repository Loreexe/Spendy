# Spendy — Design

Identità visiva e sistema di design dell'interfaccia (tema scuro di default).

## Logo

Gli asset stanno in `apps/frontend/public/logo/` (dettagli in `logo/README.md`):

- simbolo a due tessere con foro che compongono una **S**, colore primario
  **`#1DB48B`** (su fondi chiari `#166047`);
- lockup integrato **`[logo]pendy`** in orizzontale (il simbolo sostituisce la
  S iniziale); lockup verticale con simbolo sopra e scritta per esteso;
- tre lockup senza tagline (orizzontale, verticale, solo simbolo), versioni
  colore su scuro/chiaro e mono bianco/nero;
- favicon, icone PWA (192/512 + maskable), immagine OG e foreground adattivo.

Uso: gradiente solo nel logo, glow solo nel logo, nel login e nell'hero.
Flat/mono obbligatorio: il logo deve funzionare senza gradiente né glow,
a 16 px e in un solo colore.

## Tema

- Scuro di default (`#0B0F0D`), chiaro a parità di qualità; scelta manuale,
  niente “auto”. La preferenza è salvata nel profilo e sincronizzata.
- Token CSS in `apps/frontend/src/styles/tokens.css` (`data-theme`
  su `<html>`): fondi, testo, accento, stati, raggio 18–20 px, ombre morbide,
  motion 150–200 ms con rispetto di `prefers-reduced-motion`.

## Tipografia e icone

- Font UI: **Inter** self-hosted (400/500/600/700) in
  `apps/frontend/public/fonts/`; cifre tabulari (`.tnum`) per gli importi,
  formato `1.234,56 €`.
- Icone: Lucide. Illustrazioni: line art mint.

## Layout e componenti

- Desktop: top bar con brand e navigazione a icone. Mobile: bottom bar fissa.
- Dashboard con totali, grafici (SVG senza dipendenze) ed elenchi;
  tabelle → card su mobile; modali per CRUD brevi, pagine per flussi lunghi.
- Feedback: toast per il successo (con annullamento dove previsto), errori
  inline, modale distruttiva con riepilogo per le azioni irreversibili,
  skeleton per il caricamento.
- Cestino con ripristino e retention di 30 giorni per tutte le entità
  eliminabili.

## Accessibilità

Contrasto AA, focus visibile, navigazione da tastiera, target touch adeguati,
grafici mai comunicati solo col colore, `prefers-reduced-motion` rispettato.
