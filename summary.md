# backend-core — Investimenti: modelli, migrazione e servizio ledger

## Cosa ho fatto

- `apps/backend/finance/models.py`
  - `Profile.investment_account`: FK `Account`, null/blank, `SET_NULL`, `related_name="investment_profiles"`.
  - `Transaction.Kind`: aggiunti `INVESTMENT_BUY`, `INVESTMENT_SELL`, `INVESTMENT_DIVIDEND`. **`Transaction.kind.max_length` è passato da 16 a 19** (il valore `investment_dividend` è lungo 19; senza questo `makemigrations` falliva il system check).
  - `InvestmentPosition`: profilo, nome, categoria (stock/etf/bond/fund/crypto/real_estate/other), identificativo, prezzo corrente 18/8, data prezzo, archiviata, timestamp; ordinamento `name, id`.
  - `InvestmentOperation`: profilo, posizione `PROTECT`, tipo opening/buy/sell/dividend, data, quantità 24/8, prezzo unitario 24/8, lordo 14/2, commissione 12/2, cassa 14/2, descrizione, movimento `OneToOne Transaction` nullabile con `PROTECT`, timestamp. Vincoli DB: una sola apertura per posizione (unique parziale), cassa non negativa, movimento nullo solo per l'apertura, apertura senza cassa/commissione, quantità obbligatoria e positiva per apertura/acquisto/vendita.
- `apps/backend/finance/investments.py` (nuovo servizio)
  - `recalculate_position(position)`: ledger da operazioni ordinate per `(date, id)`; quantità, costo residuo, costo medio, valore corrente, plusvalenza non realizzata, plusvalenza realizzata, dividendi, righe per operazione (`quantity_after`, `cost_after`, `cost_removed`, `realized_gain`, `cash_flow`).
  - `position_summary(position)` e `portfolio_summary(profile)`.
  - `create_operation(...)`, `update_operation(...)`, `delete_operation(...)` con `transaction.atomic`, `select_for_update` sulla posizione, creazione/aggiornamento/eliminazione atomica di `Transaction` + `Line`.
  - `set_investment_account(profile, account)`, `set_position_archived(position, archived)`.
  - Regole: apertura senza movimento di conto; acquisto cassa `-(lordo+commissione)`; vendita cassa `+(lordo-commissione)`, costo rimosso a costo medio (intero costo se vendita totale), plusvalenza `netto - costo rimosso`; dividendo cassa `+`, costo invariato; denaro `ROUND_HALF_UP` a 2 decimali, quantità/prezzo 8 decimali; niente float.
  - Validazioni: quantità > 0, prezzo/controvalore obbligatorio e > 0, commissione >= 0, netto vendita > 0, vendita oltre la quantità posseduta alla data, apertura unica e solo come prima operazione, conto investimenti mancante/archiviato, conto che andrebbe negativo tramite `assert_accounts_non_negative`, posizione archiviata.
- `apps/backend/finance/migrations/0005_profile_investment_account_alter_transaction_kind_and_more.py`: migrazione generata.
- `apps/backend/finance/test_investments.py`: 34 test unitari (nessuna API): apertura, acquisto con commissione/controvalore, vendita parziale/totale, oversell, dividendo, modifica/eliminazione con ricalcolo e rollback, apertura duplicata/dopo altre operazioni, valore corrente/plusvalenza non realizzata, arrotondamenti frazionari, posizione non eliminabile con operazioni, archiviazione solo a quantità zero, conto negativo/mancante/archiviato, cambio conto che non riscrive lo storico, riepilogo portafoglio.

## Cosa NON ho fatto (fuori scope)

- Nessuna modifica a `views.py`, `serializers.py`, `urls.py`, `archive.py`, `export_views.py`, dashboard o frontend.
- Nessuna API, nessun export CSV, nessun aggiornamento archivio/schema 2.
- Nessun contributo, valore manuale, prezzo automatico o rendimento.

## Check eseguiti (locali)

- `makemigrations --check --dry-run`: **No changes detected**.
- `manage.py test finance.test_investments`: **34 test, OK**.
- Suite completa da `apps/backend`: **215 test, OK**.
- Nota: il comando dello spec lanciato dalla radice del worktree (`python apps/backend/manage.py test`) trova **0 test** perché la discovery parte dalla cwd; la suite reale va lanciata da `apps/backend` (come nel piano, §8.3). Da `apps/backend` sono 215/215 OK.

## Cosa deve verificare il verifier (indipendentemente)

1. Ricostruire a mano un ledger (apertura, acquisto con commissione, vendita parziale, vendita totale, dividendo) e confrontarlo con `recalculate_position`.
2. Casi avversari: oversell, apertura duplicata, apertura dopo operazioni, modifica/eliminazione che rende invalida una vendita successiva (deve fare rollback), arrotondamenti con quantità frazionarie.
3. Che il conto non vada mai negativo per acquisti/modifiche e che l'apertura non crei `Transaction`/`Line`.
4. Che modifica/eliminazione usino il conto storico dell'operazione (non il conto investimenti corrente) e che il cambio conto non riscriva lo storico.
5. Che non ci siano modifiche a views/serializers/urls/archive/export/frontend.
6. Che `Transaction.kind` a 19 caratteri sia accettabile per l'API task successivo (nessun test esistente si è rotto).

## Limiti noti / note per i task successivi

- L'archiviazione di una posizione è validata solo dal servizio `set_position_archived`: l'API dovrà chiamarlo. L'eliminazione di una posizione con operazioni è protetta dal FK `PROTECT` (solleva `ProtectedError`).
- `update_operation` non accetta il cambio di `kind` (per scelta: si elimina e ricrea).
- Le operazioni non possono essere create/modificate tramite `/transactions/`: protezione demandata al task `backend-api`.
