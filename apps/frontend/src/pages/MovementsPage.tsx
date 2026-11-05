import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  api,
  ApiError,
  type Account,
  type Category,
  type CategorySuggestion,
  type Line,
  type SavingsAccount,
  type Tag,
  type Transaction,
  type TransactionPayload,
} from "../api";
import { LoadingScreen } from "../components/Guards";
import { useToast } from "../components/Toast";
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
          {transaction.category ? ` · ${transaction.category.name}` : ""}
        </span>
        {transaction.tags.length > 0 && (
          <span className="small">
            {transaction.tags.map((tag) => (
              <span key={tag} className="badge" style={{ marginRight: "0.25rem" }}>
                {tag}
              </span>
            ))}
          </span>
        )}
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
  const { notify } = useToast();
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
  const [filterCategory, setFilterCategory] = useState("");
  const [filterTag, setFilterTag] = useState("");
  const [categories, setCategories] = useState<Category[]>([]);
  const [allTags, setAllTags] = useState<Tag[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [suggestion, setSuggestion] = useState<CategorySuggestion | null>(null);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null);
  const [editingCategoryName, setEditingCategoryName] = useState("");
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(async (limit = 200) => {
    setLoading(true);
    try {
      const [transactionsData, accountsData, savingsData, categoriesData, tagsData] =
        await Promise.all([
          api.transactions({
            account: filterAccount ? Number(filterAccount) : undefined,
            savings: filterSavings ? Number(filterSavings) : undefined,
            start: filterStart || undefined,
            end: filterEnd || undefined,
            category: filterCategory ? Number(filterCategory) : undefined,
            tag: filterTag || undefined,
            limit,
          }),
          api.accounts(),
          api.savings(),
          api.categories(),
          api.tags(),
        ]);
      setTransactions(transactionsData.transactions);
      setTotal(transactionsData.count);
      setCategories(categoriesData);
      setAllTags(tagsData);
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
  }, [filterAccount, filterSavings, filterStart, filterEnd, filterCategory, filterTag]);

  useEffect(() => {
    if (filterStart && filterEnd && filterStart > filterEnd) {
      setError("La data iniziale supera quella finale.");
      return;
    }
    setError(null);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterAccount, filterSavings, filterStart, filterEnd, filterCategory, filterTag]);

  async function loadMore() {
    setLoadingMore(true);
    setError(null);
    try {
      const data = await api.transactions({
        account: filterAccount ? Number(filterAccount) : undefined,
        savings: filterSavings ? Number(filterSavings) : undefined,
        start: filterStart || undefined,
        end: filterEnd || undefined,
        category: filterCategory ? Number(filterCategory) : undefined,
        tag: filterTag || undefined,
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
        category: filterCategory ? Number(filterCategory) : undefined,
        tag: filterTag || undefined,
      });
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function suggestForDescription(value: string) {
    const text = value.trim();
    if (text.length < 3 || categoryId) {
      if (text.length < 3) setSuggestion(null);
      return;
    }
    try {
      const account =
        kind === "income" || (kind === "expense" && expenseSource === "account")
          ? Number(accountId) || undefined
          : undefined;
      const result = await api.suggestCategory({
        description: text,
        account,
      });
      setSuggestion(result);
    } catch {
      setSuggestion(null);
    }
  }

  function clearFilters() {
    setFilterAccount("");
    setFilterSavings("");
    setFilterStart("");
    setFilterEnd("");
    setFilterCategory("");
    setFilterTag("");
  }

  async function refreshTaxonomy() {
    try {
      const [categoriesData, tagsData] = await Promise.all([
        api.categories(),
        api.tags(),
      ]);
      setCategories(categoriesData);
      setAllTags(tagsData);
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleCreateCategory() {
    const name = newCategoryName.trim();
    if (!name) return;
    setError(null);
    try {
      await api.createCategory(name);
      setNewCategoryName("");
      await refreshTaxonomy();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleRenameCategory(category: Category) {
    const name = editingCategoryName.trim();
    if (!name) return;
    setError(null);
    try {
      await api.updateCategory(category.id, name);
      setEditingCategoryId(null);
      setEditingCategoryName("");
      await refreshTaxonomy();
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDeleteCategory(category: Category) {
    setError(null);
    try {
      await api.deleteCategory(category.id);
      notify(`Categoria «${category.name}» eliminata.`, {
        label: "Annulla",
        onClick: () => {
          api
            .restoreTrash("category", category.id)
            .then(() => {
              refreshTaxonomy();
              reload();
            })
            .catch((err) => setError(errorMessage(err)));
        },
      });
      if (String(category.id) === categoryId) setCategoryId("");
      if (String(category.id) === filterCategory) setFilterCategory("");
      await refreshTaxonomy();
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleDeleteTag(tag: Tag) {
    setError(null);
    try {
      await api.deleteTag(tag.id);
      notify(`Tag «${tag.name}» eliminato.`, {
        label: "Annulla",
        onClick: () => {
          api
            .restoreTrash("tag", tag.id)
            .then(() => {
              refreshTaxonomy();
              reload();
            })
            .catch((err) => setError(errorMessage(err)));
        },
      });
      await refreshTaxonomy();
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function parseTags(): string[] {
    return tagInput
      .split(",")
      .map((item) => item.trim())
      .filter((item) => item.length > 0);
  }

  function buildPayload(): TransactionPayload | null {
    if (!amount || Number(amount) <= 0) {
      setError("Inserisci un importo maggiore di zero.");
      return null;
    }
    const category_id = categoryId ? Number(categoryId) : undefined;
    const tags = parseTags();
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
        category_id,
        tags,
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
          category_id,
          tags,
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
        category_id,
        tags,
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
      category_id: categoryId ? Number(categoryId) : undefined,
      tags: parseTags(),
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
    setCategoryId("");
    setTagInput("");
    setSuggestion(null);
  }

  function startEdit(transaction: Transaction) {
    if (transaction.kind === "opening") return;
    setEditingId(transaction.id);
    setKind(transaction.kind as Kind);
    setDate(transaction.date);
    setDescription(transaction.description);
    setAmount(transaction.amount);
    setConfirmCoverage(false);
    setCategoryId(transaction.category ? String(transaction.category.id) : "");
    setTagInput(transaction.tags.join(", "));
    setSuggestion(null);

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
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.deleteTransaction(transaction.id);
      if (editingId === transaction.id) resetForm();
      notify(
        `Movimento eliminato: ${transaction.description || transaction.kind_label}.`,
        {
          label: "Annulla",
          onClick: () => {
            api
              .restoreTrash("movement", transaction.id)
              .then(() => reload())
              .catch((err) => setError(errorMessage(err)));
          },
        },
      );
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

      <p className="muted small">
        Le operazioni di investimento (aperture, acquisti, vendite, dividendi)
        non compaiono in questo registro: le trovi nella{" "}
        <Link to="/investments">pagina Investimenti</Link>. Gli effetti su saldo
        e patrimonio sono inclusi nella dashboard.
      </p>

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
                onBlur={(event) => void suggestForDescription(event.target.value)}
                placeholder="Facoltativa"
              />
            </label>
            <label>
              Categoria
              <select
                value={categoryId}
                onChange={(event) => {
                  setCategoryId(event.target.value);
                  setSuggestion(null);
                }}
              >
                <option value="">Altro (automatica)</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tag (separati da virgola)
              <input
                value={tagInput}
                onChange={(event) => setTagInput(event.target.value)}
                placeholder="Facoltativi"
              />
            </label>
          </div>
          {suggestion && !categoryId && (
            <p className="muted small">
              Categoria suggerita: <strong>{suggestion.category.name}</strong>{" "}
              <button
                type="button"
                className="secondary"
                onClick={() => {
                  setCategoryId(String(suggestion.category.id));
                  setSuggestion(null);
                }}
              >
                Usa
              </button>
            </p>
          )}

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
            <label>
              <span className="small muted">Categoria</span>
              <select
                value={filterCategory}
                onChange={(event) => setFilterCategory(event.target.value)}
              >
                <option value="">Tutte le categorie</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span className="small muted">Tag</span>
              <input
                value={filterTag}
                onChange={(event) => setFilterTag(event.target.value)}
                placeholder="Tutti i tag"
              />
            </label>
            {(filterAccount ||
              filterSavings ||
              filterStart ||
              filterEnd ||
              filterCategory ||
              filterTag) && (
              <button
                type="button"
                className="secondary"
                onClick={clearFilters}
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
          e possono essere usati da soli o insieme agli altri filtri. «Categoria»
          e «Tag» filtrano per classificazione. «Esporta CSV» scarica i movimenti
          filtrati. Il registro mostra prima i movimenti più recenti.
        </p>
        {transactions.length === 0 ? (
          <p className="muted">
            {filterAccount || filterSavings || filterCategory || filterTag
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

      <section className="card">
        <div className="card-heading">
          <h2>Categorie e tag</h2>
        </div>
        <p className="muted small">
          Ogni movimento ha una categoria (i nuovi movimenti senza categoria
          vanno su «Altro») e zero o più tag. «Altro» non si può rinominare né
          eliminare; eliminando una categoria i suoi movimenti passano ad
          «Altro».
        </p>
        <ul className="entity-list">
          {categories.map((category) => (
            <li key={category.id}>
              {editingCategoryId === category.id ? (
                <span className="inline-form">
                  <input
                    value={editingCategoryName}
                    onChange={(event) =>
                      setEditingCategoryName(event.target.value)
                    }
                    maxLength={60}
                  />
                  <button
                    type="button"
                    onClick={() => void handleRenameCategory(category)}
                  >
                    Salva
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    onClick={() => setEditingCategoryId(null)}
                  >
                    Annulla
                  </button>
                </span>
              ) : (
                <>
                  <span>
                    {category.name}{" "}
                    {category.is_default && (
                      <span className="badge">Iniziale</span>
                    )}{" "}
                    {category.is_preset && !category.is_default && (
                      <span className="badge">Predefinita</span>
                    )}
                  </span>
                  {!category.is_default && (
                    <span className="entity-side">
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => {
                          setEditingCategoryId(category.id);
                          setEditingCategoryName(category.name);
                        }}
                      >
                        Rinomina
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => void handleDeleteCategory(category)}
                      >
                        Elimina
                      </button>
                    </span>
                  )}
                </>
              )}
            </li>
          ))}
        </ul>
        <div className="inline-form" style={{ marginTop: "0.75rem" }}>
          <input
            value={newCategoryName}
            onChange={(event) => setNewCategoryName(event.target.value)}
            placeholder="Nuova categoria"
            maxLength={60}
          />
          <button type="button" onClick={() => void handleCreateCategory()}>
            Aggiungi
          </button>
        </div>
        {allTags.length > 0 && (
          <>
            <div className="card-heading" style={{ marginTop: "1rem" }}>
              <h2>Tag usati</h2>
            </div>
            <p className="small">
              {allTags.map((tag) => (
                <span
                  key={tag.id}
                  className="badge"
                  style={{ marginRight: "0.25rem" }}
                >
                  {tag.name}{" "}
                  <button
                    type="button"
                    className="link-button"
                    aria-label={`Elimina tag ${tag.name}`}
                    onClick={() => void handleDeleteTag(tag)}
                    style={{ color: "inherit", fontWeight: 700 }}
                  >
                    ×
                  </button>
                </span>
              ))}
            </p>
          </>
        )}
      </section>
    </div>
  );
}
