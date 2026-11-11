import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { useSearchParams } from "react-router-dom";
import { Tags, X } from "lucide-react";
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
import { EmptyState } from "../components/EmptyState";
import { CategoryIcon } from "../components/CategoryIcon";
import { CategoryIconPicker } from "../components/CategoryIconPicker";
import { CategorySelect } from "../components/CategorySelect";
import { useToast } from "../components/Toast";
import {
  amountClass,
  currentTimeHM,
  formatDate,
  money,
  normalizeTime,
  signedMoney,
  todayISO,
} from "../format";

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
  const time = normalizeTime(transaction.time);
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
          {formatDate(transaction.date)}
          {time ? ` · ${time}` : ""} · {transaction.kind_label}
          {transaction.category ? (
            <>
              {" · "}
              <span className="movement-category">
                <CategoryIcon name={transaction.category.icon} size={14} />
                {transaction.category.name}
              </span>
            </>
          ) : null}
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
  const [searchParams, setSearchParams] = useSearchParams();
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
  const [time, setTime] = useState(currentTimeHM());
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const amountInputRef = useRef<HTMLInputElement | null>(null);
  const formRef = useRef<HTMLElement | null>(null);

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
  const [newCategoryIcon, setNewCategoryIcon] = useState("tag");
  const [editingCategoryId, setEditingCategoryId] = useState<number | null>(null);
  const [editingCategoryName, setEditingCategoryName] = useState("");
  const [editingCategoryIcon, setEditingCategoryIcon] = useState("tag");
  const [editingTagId, setEditingTagId] = useState<number | null>(null);
  const [editingTagName, setEditingTagName] = useState("");
  const [taxonomyOpen, setTaxonomyOpen] = useState(false);

  useEffect(() => {
    if (!taxonomyOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setTaxonomyOpen(false);
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [taxonomyOpen]);

  // `?new=expense|transfer|income` (azioni rapide della Home): preseleziona il
  // tipo, porta al form, mette il focus sull'importo e ripulisce il parametro.
  useEffect(() => {
    const requested = searchParams.get("new");
    if (!requested) return;
    if (requested === "income" || requested === "expense" || requested === "transfer") {
      resetForm();
      setKind(requested);
    }
    const timer = window.setTimeout(() => {
      const reduceMotion =
        window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
      formRef.current?.scrollIntoView({
        behavior: reduceMotion ? "auto" : "smooth",
        block: "start",
      });
      amountInputRef.current?.focus({ preventScroll: true });
      const params = new URLSearchParams(searchParams);
      params.delete("new");
      setSearchParams(params, { replace: true });
    }, 0);
    return () => window.clearTimeout(timer);
  }, [searchParams, setSearchParams]);

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
      await api.createCategory(name, newCategoryIcon);
      setNewCategoryName("");
      setNewCategoryIcon("tag");
      await refreshTaxonomy();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  function startCategoryEdit(category: Category) {
    setEditingCategoryId(category.id);
    setEditingCategoryName(category.name);
    setEditingCategoryIcon(category.icon || "tag");
  }

  function cancelCategoryEdit() {
    setEditingCategoryId(null);
    setEditingCategoryName("");
    setEditingCategoryIcon("tag");
  }

  async function handleSaveCategory(category: Category) {
    const name = editingCategoryName.trim();
    if (!category.is_default && !name) return;
    setError(null);
    try {
      await api.updateCategory(
        category.id,
        category.is_default
          ? { icon: editingCategoryIcon }
          : { name, icon: editingCategoryIcon },
      );
      cancelCategoryEdit();
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
      if (editingCategoryId === category.id) cancelCategoryEdit();
      await refreshTaxonomy();
      await reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function handleRenameTag(tag: Tag) {
    const name = editingTagName.trim();
    if (!name) return;
    setError(null);
    try {
      await api.updateTag(tag.id, name);
      setEditingTagId(null);
      setEditingTagName("");
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
    if (!time) {
      setError("Inserisci l'ora del movimento.");
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
        time,
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
          time,
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
        time,
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
      time,
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
    setTime(currentTimeHM());
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
    setTime(normalizeTime(transaction.time) ?? "12:00");
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

  const filtersActive = Boolean(
    filterAccount ||
      filterSavings ||
      filterStart ||
      filterEnd ||
      filterCategory ||
      filterTag,
  );

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

      <section className="card" ref={formRef}>
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
              Ora
              <input
                type="time"
                value={time}
                onChange={(event) => setTime(event.target.value)}
                required
              />
            </label>
            <label>
              Importo
              <input
                ref={amountInputRef}
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
            <div className="form-field">
              <span>Categoria</span>
              <span className="field-row">
                <CategorySelect
                  categories={categories}
                  value={categoryId}
                  onChange={(value) => {
                    setCategoryId(value);
                    setSuggestion(null);
                  }}
                  emptyLabel="Altro (automatica)"
                  ariaLabel="Categoria del movimento"
                />
                <button
                  type="button"
                  className="icon-button"
                  title="Gestisci categorie e tag"
                  aria-label="Gestisci categorie e tag"
                  onClick={() => setTaxonomyOpen(true)}
                >
                  <Tags size={18} aria-hidden="true" />
                </button>
              </span>
            </div>
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
              Categoria suggerita:{" "}
              <CategoryIcon name={suggestion.category.icon} size={14} />{" "}
              <strong>{suggestion.category.name}</strong>{" "}
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
          <div className="filters">
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
            <div className="filter-category">
              <span className="small muted">Categoria</span>
              <CategorySelect
                categories={categories}
                value={filterCategory}
                onChange={setFilterCategory}
                emptyLabel="Tutte le categorie"
                ariaLabel="Filtra per categoria"
              />
            </div>
            <label>
              <span className="small muted">Tag</span>
              <input
                value={filterTag}
                onChange={(event) => setFilterTag(event.target.value)}
                placeholder="Tutti i tag"
              />
            </label>
            <div className="actions">
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
            </div>
          </div>
        </div>
        {transactions.length === 0 ? (
          <EmptyState
            illustration="movements"
            title={
              filtersActive
                ? "Nessun movimento per questo filtro"
                : "Nessun movimento registrato"
            }
            description={
              filtersActive
                ? "Prova a cambiare conto, periodo, categoria o tag per vedere più movimenti."
                : "Registra la prima entrata, spesa o trasferimento: comparirà qui nel registro."
            }
            actionLabel={filtersActive ? "Mostra tutto" : "Aggiungi movimento"}
            onAction={
              filtersActive
                ? clearFilters
                : () => amountInputRef.current?.focus()
            }
          />
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

      {taxonomyOpen && (
        <div className="modal-backdrop" onClick={() => setTaxonomyOpen(false)}>
          <div
            className="modal modal-wide"
            role="dialog"
            aria-modal="true"
            aria-label="Categorie e tag"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="card-heading">
              <h2>Categorie e tag</h2>
              <button
                type="button"
                className="modal-close"
                aria-label="Chiudi gestione categorie"
                onClick={() => setTaxonomyOpen(false)}
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>
            <ul className="entity-list">
              {categories.map((category) => (
                <li key={category.id}>
                  {editingCategoryId === category.id ? (
                    <div className="taxonomy-editor">
                      {category.is_default ? (
                        <span className="taxonomy-entry-name">
                          <CategoryIcon
                            name={editingCategoryIcon}
                            size={18}
                          />
                          {category.name}
                        </span>
                      ) : (
                        <div className="inline-form">
                          <input
                            value={editingCategoryName}
                            onChange={(event) =>
                              setEditingCategoryName(event.target.value)
                            }
                            maxLength={60}
                            aria-label={`Nome della categoria ${category.name}`}
                          />
                        </div>
                      )}
                      <CategoryIconPicker
                        label="Icona della categoria"
                        value={editingCategoryIcon}
                        onChange={setEditingCategoryIcon}
                      />
                      <div className="actions">
                        <button
                          type="button"
                          onClick={() => void handleSaveCategory(category)}
                        >
                          Salva
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          onClick={cancelCategoryEdit}
                        >
                          Annulla
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <span className="taxonomy-entry-name">
                        <CategoryIcon name={category.icon} size={18} />
                        <span>
                          {category.name}{" "}
                          {category.is_default && (
                            <span className="badge">Iniziale</span>
                          )}{" "}
                          {category.is_preset && !category.is_default && (
                            <span className="badge">Predefinita</span>
                          )}
                        </span>
                      </span>
                      <span className="entity-side">
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => startCategoryEdit(category)}
                        >
                          {category.is_default ? "Cambia icona" : "Modifica"}
                        </button>
                        {!category.is_default && (
                          <button
                            type="button"
                            className="danger"
                            onClick={() => void handleDeleteCategory(category)}
                          >
                            Elimina
                          </button>
                        )}
                      </span>
                    </>
                  )}
                </li>
              ))}
            </ul>
            <div className="taxonomy-create">
              <div className="inline-form">
                <input
                  value={newCategoryName}
                  onChange={(event) => setNewCategoryName(event.target.value)}
                  placeholder="Nuova categoria"
                  maxLength={60}
                  aria-label="Nome della nuova categoria"
                />
                <button type="button" onClick={() => void handleCreateCategory()}>
                  Aggiungi
                </button>
              </div>
              <CategoryIconPicker
                label="Icona della nuova categoria"
                value={newCategoryIcon}
                onChange={setNewCategoryIcon}
              />
            </div>
            {allTags.length > 0 && (
              <>
                <div className="card-heading" style={{ marginTop: "1rem" }}>
                  <h2>Tag usati</h2>
                </div>
                <p className="small">
                  {allTags.map((tag) =>
                    editingTagId === tag.id ? (
                      <span key={tag.id} className="inline-form">
                        <input
                          value={editingTagName}
                          onChange={(event) =>
                            setEditingTagName(event.target.value)
                          }
                          maxLength={30}
                        />
                        <button
                          type="button"
                          onClick={() => void handleRenameTag(tag)}
                        >
                          Salva
                        </button>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setEditingTagId(null)}
                        >
                          Annulla
                        </button>
                      </span>
                    ) : (
                      <span
                        key={tag.id}
                        className="badge"
                        style={{ marginRight: "0.25rem" }}
                      >
                        {tag.name}{" "}
                        <button
                          type="button"
                          className="link-button"
                          aria-label={`Rinomina tag ${tag.name}`}
                          onClick={() => {
                            setEditingTagId(tag.id);
                            setEditingTagName(tag.name);
                          }}
                          style={{ color: "inherit", fontWeight: 700 }}
                        >
                          ✎
                        </button>{" "}
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
                    ),
                  )}
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
