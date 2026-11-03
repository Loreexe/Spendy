import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  ApiError,
  type Account,
  type Line,
  type SavingsAccount,
  type Transaction,
  type TransactionPayload,
} from "../api";
import { LoadingScreen } from "../components/Guards";
import { amountClass, money, signedMoney, todayISO } from "../format";

type Kind = "income" | "expense" | "transfer";
type SourceKind = "account" | "savings";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    const data = (err.data ?? {}) as Record<string, unknown>;
    for (const key of ["confirm_coverage", "detail", "amount", "account", "savings"]) {
      const value = data[key];
      if (typeof value === "string") return value;
      if (Array.isArray(value) && typeof value[0] === "string") return value[0];
    }
    return err.message;
  }
  return err instanceof Error ? err.message : "Operazione non riuscita.";
}

function lineLabel(line: Line): string {
  const target = line.account_name ?? line.savings_name ?? "—";
  const role =
    line.role === "technical"
      ? " · tecnico"
      : line.role === "transfer_out"
        ? " · uscita"
        : line.role === "transfer_in"
          ? " · entrata"
          : "";
  return `${target}${role}`;
}

function MovementItem({
  transaction,
  onDelete,
  onEdit,
}: {
  transaction: Transaction;
  onDelete: (transaction: Transaction) => void;
  onEdit: (transaction: Transaction) => void;
}) {
  return (
    <li className="movement-row">
      <div className="movement-main">
        <div className="movement-title">
          <strong>{transaction.description || transaction.kind_label}</strong>
          <span className={`money ${amountClass(transaction.amount)}`}>
            {money(transaction.amount)}
          </span>
        </div>
        <span className="muted small">
          {new Date(`${transaction.date}T12:00:00`).toLocaleDateString("it-IT")} ·{" "}
          {transaction.kind_label}
        </span>
        <ul className="lines">
          {transaction.lines.map((line) => (
            <li key={line.id}>
              <span>{lineLabel(line)}</span>
              <span className={amountClass(line.amount)}>
                {signedMoney(line.amount)}
              </span>
            </li>
          ))}
        </ul>
      </div>
      {transaction.kind !== "opening" && (
        <div className="actions">
          <button
            type="button"
            className="secondary"
            onClick={() => onEdit(transaction)}
          >
            Modifica
          </button>
          <button
            type="button"
            className="danger"
            onClick={() => onDelete(transaction)}
          >
            Elimina
          </button>
        </div>
      )}
    </li>
  );
}

export function MovementsPage() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [savings, setSavings] = useState<SavingsAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [kind, setKind] = useState<Kind>("expense");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [date, setDate] = useState(todayISO());
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");

  const [accountId, setAccountId] = useState("");
  const [savingsId, setSavingsId] = useState("");
  const [expenseSource, setExpenseSource] = useState<SourceKind>("account");
  const [confirmCoverage, setConfirmCoverage] = useState(false);

  const [fromKind, setFromKind] = useState<SourceKind>("account");
  const [fromAccountId, setFromAccountId] = useState("");
  const [fromSavingsId, setFromSavingsId] = useState("");
  const [toKind, setToKind] = useState<SourceKind>("account");
  const [toAccountId, setToAccountId] = useState("");
  const [toSavingsId, setToSavingsId] = useState("");

  const [filterAccount, setFilterAccount] = useState("");
  const [filterSavings, setFilterSavings] = useState("");
  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(async (limit = 200) => {
    setLoading(true);
    try {
      const [transactionsData, accountsData, savingsData] = await Promise.all([
        api.transactions({
          account: filterAccount ? Number(filterAccount) : undefined,
          savings: filterSavings ? Number(filterSavings) : undefined,
          start: filterStart || undefined,
          end: filterEnd || undefined,
          limit,
        }),
        api.accounts(),
        api.savings(),
      ]);
      setTransactions(transactionsData.transactions);
      setTotal(transactionsData.count);
      const activeAccounts = accountsData.accounts.filter((item) => !item.archived);
      setAccounts(activeAccounts);
      setSavings(savingsData.savings);
      setAccountId((current) => current || String(activeAccounts[0]?.id ?? ""));
      setFromAccountId((current) => current || String(activeAccounts[0]?.id ?? ""));
      setToAccountId((current) => current || String(activeAccounts[0]?.id ?? ""));
      setSavingsId((current) => current || String(savingsData.savings[0]?.id ?? ""));
      setFromSavingsId(
        (current) => current || String(savingsData.savings[0]?.id ?? ""),
      );
      setToSavingsId(
        (current) => current || String(savingsData.savings[0]?.id ?? ""),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [filterAccount, filterSavings, filterStart, filterEnd]);

  useEffect(() => {
    if (filterStart && filterEnd && filterStart > filterEnd) {
      setError("La data iniziale supera quella finale.");
      return;
    }
    setError(null);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterAccount, filterSavings, filterStart, filterEnd]);

  async function loadMore() {
    setLoadingMore(true);
    setError(null);
    try {
      const data = await api.transactions({
        account: filterAccount ? Number(filterAccount) : undefined,
        savings: filterSavings ? Number(filterSavings) : undefined,
        start: filterStart || undefined,
        end: filterEnd || undefined,
        limit: 200,
        offset: transactions.length,
      });
      setTransactions((current) => [...current, ...data.transactions]);
      setTotal(data.count);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoadingMore(false);
    }
  }

  function reload() {
    return load(Math.max(200, transactions.length));
  }

  async function exportCsv() {
    setError(null);
    try {
      await api.exportTransactions({
        account: filterAccount ? Number(filterAccount) : undefined,
        savings: filterSavings ? Number(filterSavings) : undefined,
        start: filterStart || undefined,
        end: filterEnd || undefined,
      });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function buildPayload(): TransactionPayload | null {
    if (!amount || Number(amount) <= 0) {
      setError("Inserisci un importo maggiore di zero.");
      return null;
    }
    if (kind === "income") {
      if (!accountId) {
        setError("Seleziona il conto dell'entrata.");
        return null;
      }
      return {
        kind,
        date,
        description,
        amount,
        account: Number(accountId),
      };
    }
    if (kind === "expense") {
      if (expenseSource === "account") {
        if (!accountId) {
          setError("Seleziona il conto della spesa.");
          return null;
        }
        return {
          kind,
          date,
          description,
          amount,
          account: Number(accountId),
        };
      }
      if (!savingsId) {
        setError("Seleziona il salvadanaio della spesa.");
        return null;
      }
      return {
        kind,
        date,
        description,
        amount,
        savings: Number(savingsId),
        confirm_coverage: confirmCoverage,
      };
    }

    if (fromKind === "savings" && toKind === "savings") {
      setError("Il trasferimento diretto tra salvadanai non è ammesso.");
      return null;
    }
    const payload: TransactionPayload = {
      kind: "transfer",
      date,
      description,
      amount,
    };
    if (fromKind === "account") {
      if (!fromAccountId) {
        setError("Seleziona il conto di origine.");
        return null;
      }
      payload.from_account = Number(fromAccountId);
    } else {
      if (!fromSavingsId) {
        setError("Seleziona il salvadanaio di origine.");
        return null;
      }
      payload.from_savings = Number(fromSavingsId);
    }
    if (toKind === "account") {
      if (!toAccountId) {
        setError("Seleziona il conto di destinazione.");
        return null;
      }
      payload.to_account = Number(toAccountId);
    } else {
      if (!toSavingsId) {
        setError("Seleziona il salvadanaio di destinazione.");
        return null;
      }
      payload.to_savings = Number(toSavingsId);
    }
    return payload;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const payload = buildPayload();
    if (!payload) return;
    setBusy(true);
    try {
      if (editingId) {
        await api.updateTransaction(editingId, payload);
        setMessage("Movimento aggiornato.");
      } else {
        await api.createTransaction(payload);
        setMessage("Movimento registrato.");
      }
      resetForm();
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function resetForm() {
    setEditingId(null);
    setDate(todayISO());
    setDescription("");
    setAmount("");
    setConfirmCoverage(false);
  }

  function startEdit(transaction: Transaction) {
    if (transaction.kind === "opening") return;
    setEditingId(transaction.id);
    setKind(transaction.kind as Kind);
    setDate(transaction.date);
    setDescription(transaction.description);
    setAmount(transaction.amount);
    setConfirmCoverage(false);

    if (transaction.kind === "income") {
      const line = transaction.lines.find(
        (item) => item.target_type === "account" && item.role === "principal",
      );
      if (line?.account) setAccountId(String(line.account));
    } else if (transaction.kind === "expense") {
      const savingsLine = transaction.lines.find(
        (item) => item.target_type === "savings" && item.role === "principal",
      );
      if (savingsLine?.savings) {
        setExpenseSource("savings");
        setSavingsId(String(savingsLine.savings));
        const paidFromSavings = Math.abs(Number(savingsLine.amount));
        if (paidFromSavings < Number(transaction.amount)) {
          setConfirmCoverage(true);
        }
      } else {
        const accountLine = transaction.lines.find(
          (item) => item.target_type === "account" && item.role === "principal",
        );
        setExpenseSource("account");
        if (accountLine?.account) setAccountId(String(accountLine.account));
      }
    } else if (transaction.kind === "transfer") {
      const outLine = transaction.lines.find(
        (item) => item.role === "transfer_out",
      );
      const inLine = transaction.lines.find(
        (item) => item.role === "transfer_in",
      );
      if (outLine?.target_type === "account" && outLine.account) {
        setFromKind("account");
        setFromAccountId(String(outLine.account));
      } else if (outLine?.target_type === "savings" && outLine.savings) {
        setFromKind("savings");
        setFromSavingsId(String(outLine.savings));
      }
      if (inLine?.target_type === "account" && inLine.account) {
        setToKind("account");
        setToAccountId(String(inLine.account));
      } else if (inLine?.target_type === "savings" && inLine.savings) {
        setToKind("savings");
        setToSavingsId(String(inLine.savings));
      }
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function remove(transaction: Transaction) {
    if (!window.confirm("Eliminare questo movimento?")) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.deleteTransaction(transaction.id);
      if (editingId === transaction.id) resetForm();
      setMessage("Movimento eliminato.");
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading && transactions.length === 0) return <LoadingScreen />;

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Registro</p>
          <h1>Movimenti</h1>
        </div>
      </section>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <section className="card">
        <div className="card-heading">
          <h2>{editingId ? "Modifica movimento" : "Nuovo movimento"}</h2>
          {editingId && (
            <button type="button" className="secondary" onClick={resetForm}>
              Annulla modifica
            </button>
          )}
        </div>
        <form onSubmit={handleSubmit} className="stack">
          <div className="form-grid">
            <label>
              Tipo
              <select
                value={kind}
                onChange={(event) => setKind(event.target.value as Kind)}
              >
                <option value="income">Entrata</option>
                <option value="expense">Spesa</option>
                <option value="transfer">Trasferimento</option>
              </select>
            </label>
            <label>
              Data
              <input
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                required
              />
            </label>
            <label>
              Importo
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </label>
            <label>
              Descrizione
              <input
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Facoltativa"
              />
            </label>
          </div>

          {kind === "income" && (
            <label>
              Conto
              <select
                value={accountId}
                onChange={(event) => setAccountId(event.target.value)}
                required
              >
                <option value="">Seleziona…</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name} · {money(account.balance)}
                  </option>
                ))}
              </select>
            </label>
          )}

          {kind === "expense" && (
            <>
              <label>
                Pagato da
                <select
                  value={expenseSource}
                  onChange={(event) =>
                    setExpenseSource(event.target.value as SourceKind)
                  }
                >
                  <option value="account">Conto</option>
                  <option value="savings">Salvadanaio</option>
                </select>
              </label>
              {expenseSource === "account" ? (
                <label>
                  Conto
                  <select
                    value={accountId}
                    onChange={(event) => setAccountId(event.target.value)}
                    required
                  >
                    <option value="">Seleziona…</option>
                    {accounts.map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name} · {money(account.balance)}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <>
                  <label>
                    Salvadanaio
                    <select
                      value={savingsId}
                      onChange={(event) => setSavingsId(event.target.value)}
                      required
                    >
                      <option value="">Seleziona…</option>
                      {savings.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name} · {money(item.balance)}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="checkbox-row">
                    <input
                      type="checkbox"
                      checked={confirmCoverage}
                      onChange={(event) => setConfirmCoverage(event.target.checked)}
                    />
                    Se il salvadanaio non basta, usa il conto di appoggio
                  </label>
                </>
              )}
            </>
          )}

          {kind === "transfer" && (
            <>
              <div className="form-grid">
                <label>
                  Da
                  <select
                    value={fromKind}
                    onChange={(event) =>
                      setFromKind(event.target.value as SourceKind)
                    }
                  >
                    <option value="account">Conto</option>
                    <option value="savings">Salvadanaio</option>
                  </select>
                </label>
                {fromKind === "account" ? (
                  <label>
                    Conto di origine
                    <select
                      value={fromAccountId}
                      onChange={(event) => setFromAccountId(event.target.value)}
                      required
                    >
                      <option value="">Seleziona…</option>
                      {accounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.name} · {money(account.balance)}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <label>
                    Salvadanaio di origine
                    <select
                      value={fromSavingsId}
                      onChange={(event) => setFromSavingsId(event.target.value)}
                      required
                    >
                      <option value="">Seleziona…</option>
                      {savings.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name} · {money(item.balance)}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  A
                  <select
                    value={toKind}
                    onChange={(event) => setToKind(event.target.value as SourceKind)}
                  >
                    <option value="account">Conto</option>
                    <option value="savings">Salvadanaio</option>
                  </select>
                </label>
                {toKind === "account" ? (
                  <label>
                    Conto di destinazione
                    <select
                      value={toAccountId}
                      onChange={(event) => setToAccountId(event.target.value)}
                      required
                    >
                      <option value="">Seleziona…</option>
                      {accounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <label>
                    Salvadanaio di destinazione
                    <select
                      value={toSavingsId}
                      onChange={(event) => setToSavingsId(event.target.value)}
                      required
                    >
                      <option value="">Seleziona…</option>
                      {savings.map((item) => (
                        <option key={item.id} value={item.id}>
                          {item.name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
              <p className="muted small">
                I trasferimenti non sono entrate né uscite. Il trasferimento
                diretto tra salvadanai non è ammesso.
              </p>
            </>
          )}

          <button type="submit" disabled={busy}>
            {busy
              ? "Registrazione…"
              : editingId
                ? "Salva modifiche"
                : "Registra movimento"}
          </button>
        </form>
      </section>

      <section className="card">
        <div className="card-heading">
          <h2>
            Registro{" "}
            {total > transactions.length
              ? `(${transactions.length} di ${total})`
              : `(${total})`}
          </h2>
          <div className="inline-form">
            <label>
              <span className="small muted">Conto</span>
              <select
                value={filterAccount}
                onChange={(event) => {
                  setFilterAccount(event.target.value);
                  setFilterSavings("");
                }}
              >
                <option value="">Tutti i conti</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="small muted">Salvadanaio</span>
              <select
                value={filterSavings}
                onChange={(event) => {
                  setFilterSavings(event.target.value);
                  setFilterAccount("");
                }}
              >
                <option value="">Tutti i salvadanai</option>
                {savings.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="small muted">Dal</span>
              <input
                type="date"
                value={filterStart}
                onChange={(event) => setFilterStart(event.target.value)}
              />
            </label>
            <label>
              <span className="small muted">Al</span>
              <input
                type="date"
                value={filterEnd}
                onChange={(event) => setFilterEnd(event.target.value)}
              />
            </label>
            {(filterAccount || filterSavings || filterStart || filterEnd) && (
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setFilterAccount("");
                  setFilterSavings("");
                  setFilterStart("");
                  setFilterEnd("");
                }}
              >
                Mostra tutto
              </button>
            )}
            <button
              type="button"
              className="secondary"
              onClick={() => void exportCsv()}
            >
              Esporta CSV
            </button>
          </div>
        </div>
        <p className="muted small">
          Un movimento appartiene a un conto oppure a un salvadanaio: scegliendo
          un filtro l&apos;altro viene azzerato. «Dal» e «Al» limitano il periodo
          e possono essere usati da soli o insieme agli altri filtri. «Esporta
          CSV» scarica i movimenti filtrati. Il registro mostra prima i
          movimenti più recenti.
        </p>
        {transactions.length === 0 ? (
          <p className="muted">
            {filterAccount || filterSavings
              ? "Nessun movimento per questo filtro."
              : "Nessun movimento registrato."}
          </p>
        ) : (
          <>
            <ul className="movement-list">
              {transactions.map((transaction) => (
                <MovementItem
                  key={transaction.id}
                  transaction={transaction}
                  onDelete={remove}
                  onEdit={startEdit}
                />
              ))}
            </ul>
            {transactions.length < total && (
              <div className="actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={loadMore}
                  disabled={loadingMore}
                >
                  {loadingMore
                    ? "Caricamento…"
                    : `Carica altri (${total - transactions.length} rimanenti)`}
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
