# Spendy — Design system (livello operativo)

Questo livello rende **usabile e verificabile** il design system già esistente: catalogo dei
componenti reali, regole di layout e navigazione, matrice delle piattaforme, controlli e stato di
decisioni/eccezioni. Non introduce valori nuovi: li **riferisce** alle fonti autorevoli.

Il design system di prodotto è già documentato e implementato: **non esiste un secondo sistema**.
`design/` è il ponte tra la documentazione normativa e il codice che un agente o una persona
modificano ogni giorno.

## Gerarchia delle fonti

| Livello | Dove | Cosa contiene | Autorità |
| --- | --- | --- | --- |
| 1. Decisioni | `.spendy-wiki/DECISIONS.md`, `.spendy-wiki/UX.md` (privata) | decisioni approvate `DC-*`, UX di prodotto | approvazione dell'utente |
| 2. Normativa pubblica | [`DESIGN.md`](../DESIGN.md) | identità, palette, tipografia, componenti, accessibilità | documento normativo per l'implementazione |
| 3. Operativo | `design/` (questa cartella) | catalogo, layout, piattaforme, verifiche, stato e proposte | non decide: registra e rimanda |
| 4. Rappresentazione | [`docs/design/`](../docs/design/README.md) | tavola grafica e poster generati dai sorgenti | output, non fonte |
| 5. Codice | `apps/frontend/src/styles/tokens.css`, `apps/android/.../ui/theme/` | valori effettivamente usati | fonte autorevole dei token |

Regola: **nessun valore di stile viene ricopiato qui**. Se un valore cambia, cambia nella fonte
(codice) e si aggiorna `DESIGN.md`; `design/` si aggiorna solo per catalogo, regole, stato e
verifiche.

## File

| File | Contenuto |
| --- | --- |
| [`principles.md`](./principles.md) | principi visivi e di interazione, con stato (approvato/osservato) |
| [`tokens.md`](./tokens.md) | fonte autorevole dei token web/Android, valori derivati, regole di modifica |
| [`components.md`](./components.md) | catalogo dei componenti reali: percorso, varianti, stati, adozione |
| [`layout-rules.md`](./layout-rules.md) | shell, breakpoint reali, navigazione web/mobile, pattern di pagina |
| [`platform-matrix.md`](./platform-matrix.md) | client effettivi/pianificati, parti condivise, differenze intenzionali |
| [`verification.md`](./verification.md) | controlli esistenti, scenari, limiti noti |
| [`decisions.md`](./decisions.md) | decisioni approvate, convenzioni osservate, proposte, deprecati |
| [`maintenance.md`](./maintenance.md) | procedura per ogni modifica UI (fallback pubblico della skill) |
| [`checks/check_design.py`](./checks/check_design.py) | controlli statici mirati (token, valori grezzi, parità Android) |

## Client effettivamente presenti

| Client | Stato | Dove |
| --- | --- | --- |
| Web desktop | implementato e distribuito | `apps/frontend` (React/TypeScript + CSS puro) |
| Web mobile | implementato: **stessa SPA responsive**, non un client separato | `apps/frontend`, breakpoint ≤760 px |
| PWA installabile | manifest presente, **nessun service worker**: solo online | `apps/frontend/public/manifest.webmanifest` |
| Android nativo | implementato con limiti dichiarati (Fase Q, `0.8.4`) | `apps/android` (Kotlin + Jetpack Compose) |
| Altri client (iOS, desktop nativo) | **non previsti** | — |

## Lessico obbligatorio

| Stato | Significato |
| --- | --- |
| **Esistente** | osservato nel codice; non implica approvazione |
| **Approvato** | decisione esplicita dell'utente (`DC-*`) o regola normativa già presente |
| **Proposto** | raccomandazione dell'agente, non ancora adottata |
| **Deprecato** | ancora presente, ma da non usare per nuovo codice (serve approvazione) |

Le incoerenze attuali **non sono standard**: sono elencate come esistenti o proposte in
[`decisions.md`](./decisions.md).

## Prima di una modifica UI

1. Leggi `DESIGN.md` e i file di `design/` pertinenti (almeno `tokens.md` e `components.md`).
2. Classifica il lavoro: uso esistente · estensione compatibile · nuova variante · nuova decisione.
3. Riusa token e componenti; non aggiungere valori grezzi se esiste un token adatto.
4. Se servono nuove varianti/eccezioni, proponile: **non approvarle da solo**.
5. Aggiorna nella stessa modifica i documenti di `design/` interessati.
6. Esegui i controlli di [`verification.md`](./verification.md) e dichiara quelli non eseguiti.

## Comandi verificati (stato: 2026-11-11, release `0.8.4`)

```bash
# Web: typecheck + build (verdi, 0.8.4)
cd apps/frontend && npm run lint && npm run build

# Contrasti AA dei token reali (verde, 0.8.4)
python3 docs/design/build/check_contrast.py

# Controlli statici del design system (token, valori grezzi, parità web↔Android)
python3 design/checks/check_design.py

# Android (verde: assembleDebug, 31 test unitari, lint 0 errori; nessuna prova su device/emulatore)
cd apps/android && ./gradlew :app:assembleDebug :app:testDebugUnitTest :app:lintDebug
```

## Come viene caricata la procedura

- **Convenzione del repository**: le skill di progetto vivono in `.opencode/skills/<id>/SKILL.md`
  (come `bug`, `todo`, `tdd`, …). La skill canonica `maintain-design-system` è lì ed è registrata
  nel catalogo del gestore skill DSH (collezione `opencode`, verificata in questa sessione).
- **Caricamento DSH verificato**: l'harness carica anche `.dsh/skills/<id>/SKILL.md`. Per questo la
  skill è presente anche come **wrapper** in `.dsh/skills/maintain-design-system/`: contiene solo il
  rimando alla procedura canonica, non una copia. In questa sessione è comparsa nel catalogo
  disponibile all'agente e la sua invocazione ha funzionato. `.opencode/`, `.dsh/` e `AGENTS.md`
  sono privati (esclusi da Git).
- **Punto d'ingresso affidabile**: la sezione «Design system» di `AGENTS.md` impone di leggere
  `design/` prima di ogni modifica UI, indipendentemente dal caricamento automatico della skill.
- **Fallback pubblico**: [`maintenance.md`](./maintenance.md) contiene la procedura completa, quindi
  resta disponibile a chiunque cloni il repository o usi un harness diverso (es. una sessione senza
  le cartelle private).
- **Limite dichiarato**: non esiste alcuna manutenzione automatica in background. La procedura vale
  solo nelle sessioni in cui la skill viene letta o le istruzioni di `AGENTS.md` vengono applicate;
  eventuali automazioni future vanno configurate e dichiarate esplicitamente.

## Limiti noti

- Nessun framework di test frontend, nessun test end-to-end e nessuna baseline visiva approvata:
  le verifiche web sono typecheck, build, controlli statici e ispezione manuale.
- L'app Android non è stata eseguita su emulatore/dispositivo in questa sessione: il browser non
  dimostra la correttezza del client nativo.
- La skill è privata (`.opencode/` è escluso da Git): chi usa un harness che non carica quella
  cartella deve seguire `maintenance.md` e la sezione di `AGENTS.md`.
