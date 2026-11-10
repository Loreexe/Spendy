# Manutenzione del design system — procedura

Stessa procedura della skill `maintain-design-system` (`.opencode/skills/maintain-design-system/`),
in versione pubblica: resta valida anche se la skill non viene caricata o per chi usa un altro
harness. **Non è un processo in background**: vale solo nelle sessioni in cui viene letta.

## Quando

- prima e dopo modifiche a UI, temi, token, componenti o navigazione;
- quando si aggiungono schermate, stati, breakpoint o client;
- quando una modifica rivela incoerenze o rende obsoleta la documentazione;
- durante una revisione esplicitamente richiesta del design system.

## 1. Ricognizione obbligatoria

1. Leggi `DESIGN.md`, `design/` e le istruzioni dell'agente (`AGENTS.md`).
2. Individua client, temi, componenti, token e test esistenti; **distingui implementato e
   pianificato**.
3. Controlla lo stato del repository (`git status`): non sovrascrivere lavoro dell'utente.
4. Cerca componenti e regole riutilizzabili prima di proporne di nuovi.
5. Non inventare file, comandi, test superati, screenshot o decisioni approvate.

## 2. Classifica il lavoro

| Categoria | Cosa fare |
| --- | --- |
| Uso esistente | applica token/componenti esistenti; nessuna nuova decisione |
| Estensione compatibile | aggiungi variante/stato a un componente esistente; aggiorna catalogo |
| Nuova variante/eccezione | proponi all'utente; non approvare da solo |
| Nuova decisione di identità | serve approvazione esplicita e una `DC-*` prima di implementare |

## 3. Durante la modifica

- Riusa token e componenti; niente valori grezzi se esiste un token adatto.
- Modifica la fonte autorevole (`tokens.css`, `Color.kt`), non gli output generati a mano.
- Gli stati pertinenti (hover/focus/disabled/loading/error/vuoto) vanno nel componente, non nella
  pagina.
- Conserva comportamento e logica di dominio: una manutenzione grafica non cambia i flussi.
- Modifiche proporzionate al task; il debito preesistente non pertinente si annota, non si riscrive.

## 4. Documenti da aggiornare (stessa modifica)

| Cambia | Aggiorna |
| --- | --- |
| token o tema | `DESIGN.md` §03, `design/tokens.md`, eventuale `DC-*`, tavola `docs/design/` |
| componente | `design/components.md` (varianti, stati, adozione) |
| layout o navigazione | `design/layout-rules.md`, `design/platform-matrix.md` |
| controllo o scenario | `design/verification.md` + script/CI |
| decisione o eccezione | `design/decisions.md` (+ `DECISIONS.md` privata) |

Se la documentazione non cambia, spiega brevemente perché nel riepilogo.

## 5. Verifiche

Usa gli strumenti esistenti (elenco completo e comandi in [`verification.md`](./verification.md)):

```bash
cd apps/frontend && npm run lint && npm run build
python3 docs/design/build/check_contrast.py
python3 design/checks/check_design.py
```

Aggiungi controlli solo se giustificati e autorizzati. Se mancano browser, emulatori o baseline,
**dichiara cosa non è stato verificato**: non sostituire una verifica mancante con un'affermazione
di successo. I test browser non dimostrano la correttezza del client nativo.

## 6. Criterio di completamento

Una modifica UI è completa quando:

1. rispetta le regole applicabili o esplicita le eccezioni;
2. riusa le fonti autorevoli senza duplicarle;
3. mantiene aggiornati i documenti pertinenti;
4. include verifiche proporzionate e risultati reali;
5. elenca limiti e decisioni ancora pendenti.

## 7. Modello di riepilogo finale

```text
Cosa è cambiato e perché:
File principali e fonte autorevole:
Documentazione aggiornata (o perché non serve):
Controlli eseguiti e risultato:
Controlli non eseguiti e motivo:
Decisioni/revisioni richieste:
```

## Integrazione con l'agente

- `AGENTS.md` contiene la regola minima: consultare il design system prima di ogni modifica UI,
  riusare token/componenti, aggiornare la documentazione, eseguire e dichiarare le verifiche,
  sottoporre a revisione le nuove eccezioni.
- La procedura canonica è in `.opencode/skills/maintain-design-system/SKILL.md` (privata, esclusa
  da Git). Per l'harness DSH esiste un wrapper in `.dsh/skills/maintain-design-system/SKILL.md`
  (anch'esso privato): rimanda alla canonica e a questo file, senza duplicarne il contenuto.
- Il caricamento è stato verificato in questa sessione: la skill è entrata nel catalogo disponibile
  all'agente e la sua invocazione ha funzionato. Se in un'altra sessione non viene caricata, vale
  comunque questa procedura letta dal repository.
- La sezione «Design system» di `AGENTS.md` è il punto d'ingresso che rende la regola esplicita in
  ogni sessione, indipendentemente dalla skill.
- Non promettere manutenzione automatica: non esistono hook o job che aggiornano il design system
  dopo una modifica.
