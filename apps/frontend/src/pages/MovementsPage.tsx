import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { useSearchParams } from "react-router-dom";
import { Check, Plus, Tags, X } from "lucide-react";
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
import { MovementsSkeleton } from "../components/PageSkeletons";
import { CategoryIcon } from "../components/CategoryIcon";
import { TransactionIcon } from "../components/TransactionIcon";
import { EmptyState } from "../components/EmptyState";
import { CategoryIconPicker } from "../components/CategoryIconPicker";
import { CategorySelect } from "../components/CategorySelect";
import { AppSelect } from "../components/AppSelect";
import { DateField, TimeField } from "../components/MovementDateTime";
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
      <span className="movement-leading">
        <TransactionIcon transaction={transaction} />
      </span>
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
  const [amount, setAmount] = useState("20,00");
  const amountInputRef = useRef<HTMLInputElement | null>(null);
  const formRef = useRef<HTMLDivElement | null>(null);

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
  const [composerOpen, setComposerOpen] = useState(false);
  const [formStep, setFormStep] = useState<0 | 1 | 2>(0);
  const typePillRef = useRef<HTMLDivElement | null>(null);
  const typeIndicatorRef = useRef<HTMLSpanElement | null>(null);
  const wizardLayoutRef = useRef<HTMLDivElement | null>(null);
  const confirmArmedAtRef = useRef(0);
  const [confirmReady, setConfirmReady] = useState(false);

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
    const amountValue = amount.replace(",", ".").replace(/[.,]$/, "").trim();
    if (!amountValue || Number(amountValue) <= 0) {
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
        amount: amountValue,
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
          amount: amountValue,
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
        amount: amountValue,
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
      amount: amountValue,
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
    // La conferma esiste solo al passo 3: Enter o invii impliciti non devono
    // saltare data, ora e tag.
    if (formStep < 2) {
      nextStep();
      return;
    }
    if (Date.now() - confirmArmedAtRef.current < 450) {
      return;
    }
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
    setKind("expense");
    setDate(todayISO());
    setTime(currentTimeHM());
    setDescription("");
    setAmount("20,00");
    setConfirmCoverage(false);
    setCategoryId("");
    setTagInput("");
    setSuggestion(null);
    setComposerOpen(false);
    setFormStep(0);
  }

  function startEdit(transaction: Transaction) {
    if (transaction.kind === "opening") return;
    setEditingId(transaction.id);
    setKind(transaction.kind as Kind);
    setDate(transaction.date);
    setTime(normalizeTime(transaction.time) ?? "12:00");
    setDescription(transaction.description);
    setAmount(String(transaction.amount).replace(".", ","));
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
    setComposerOpen(true);
    setFormStep(0);
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

  function numberAmount(): number {
    const parsed = Number(amount.replace(",", ".").replace(/\s/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function setAmountValue(next: number) {
    const clamped = Math.max(0, Math.round(next * 100) / 100);
    setAmount(clamped.toFixed(2).replace(".", ","));
  }

  function sanitizeAmount(raw: string): string {
    let value = raw.replace(/[^0-9.,]/g, "");
    const first = value.search(/[.,]/);
    if (first >= 0) {
      value = value.slice(0, first + 1) + value.slice(first + 1).replace(/[.,]/g, "");
    }
    return value;
  }

  function openNewMovement() {
    resetForm();
    setComposerOpen(true);
    setFormStep(0);
  }

  function closeComposer() {
    resetForm();
  }

  function accountLabel(id: string): string {
    return accounts.find((item) => String(item.id) === id)?.name ?? "—";
  }

  function savingsLabel(id: string): string {
    return savings.find((item) => String(item.id) === id)?.name ?? "—";
  }

  function sourceLabel(): string {
    if (kind === "income") return accountLabel(accountId);
    if (kind === "expense") {
      return expenseSource === "account"
        ? accountLabel(accountId)
        : savingsLabel(savingsId);
    }
    const from = fromKind === "account" ? accountLabel(fromAccountId) : savingsLabel(fromSavingsId);
    const to = toKind === "account" ? accountLabel(toAccountId) : savingsLabel(toSavingsId);
    return `${from} → ${to}`;
  }

  function categoryLabel(): string {
    return categories.find((item) => String(item.id) === categoryId)?.name ?? "Altro (automatica)";
  }

  const kindLabel = kind === "income" ? "Entrata" : kind === "expense" ? "Spesa" : "Trasferimento";
  const summaryDate = date.split("-").reverse().join("/");
  const summaryTags = tagInput.split(",").map((item) => item.trim()).filter(Boolean);

  function nextStep() {
    setError(null);
    if (formStep === 0) {
      if (numberAmount() <= 0) {
        setError("Inserisci un importo maggiore di zero.");
        return;
      }
      if (kind === "income" && !accountId) {
        setError("Seleziona il conto dell'entrata.");
        return;
      }
      if (kind === "expense") {
        if (expenseSource === "account" && !accountId) {
          setError("Seleziona il conto della spesa.");
          return;
        }
        if (expenseSource === "savings" && !savingsId) {
          setError("Seleziona il salvadanaio della spesa.");
          return;
        }
      }
      if (kind === "transfer") {
        if (fromKind === "account" && !fromAccountId) {
          setError("Seleziona il conto di origine.");
          return;
        }
        if (fromKind === "savings" && !fromSavingsId) {
          setError("Seleziona il salvadanaio di origine.");
          return;
        }
        if (toKind === "account" && !toAccountId) {
          setError("Seleziona il conto di destinazione.");
          return;
        }
        if (toKind === "savings" && !toSavingsId) {
          setError("Seleziona il salvadanaio di destinazione.");
          return;
        }
      }
    }
    setFormStep((current) => (current === 0 ? 1 : 2));
  }

  function previousStep() {
    setError(null);
    setFormStep((current) => (current === 2 ? 1 : 0));
  }

  const amountForSlider = Math.min(100, Math.max(0, numberAmount()));
  const accountOptions = accounts.map((account) => ({
    value: String(account.id),
    label: account.name,
    detail: money(account.balance),
  }));
  const savingsOptions = savings.map((item) => ({
    value: String(item.id),
    label: item.name,
    detail: money(item.balance),
  }));

  function toggleSummaryTag(name: string) {
    const current = tagInput.split(",").map((item) => item.trim()).filter(Boolean);
    const next = current.includes(name)
      ? current.filter((item) => item !== name)
      : [...current, name];
    setTagInput(next.join(", "));
  }

  useLayoutEffect(() => {
    if (!composerOpen) return;
    wizardLayoutRef.current?.scrollTo({ top: 0, behavior: "auto" });
    if (formStep === 2) {
      // Evita che un doppio clic su «Avanti» colpisca subito «Conferma».
      confirmArmedAtRef.current = Date.now();
    }
  }, [formStep, composerOpen]);

  useEffect(() => {
    if (!composerOpen || formStep !== 2) {
      setConfirmReady(false);
      return;
    }
    setConfirmReady(false);
    const timer = window.setTimeout(() => setConfirmReady(true), 450);
    return () => window.clearTimeout(timer);
  }, [formStep, composerOpen]);

  useLayoutEffect(() => {
    if (!composerOpen) return;
    const positionIndicator = () => {
      const pill = typePillRef.current;
      const indicator = typeIndicatorRef.current;
      if (!pill || !indicator) return;
      const active = pill.querySelector<HTMLButtonElement>("button.active");
      if (!active) return;
      indicator.style.width = `${active.offsetWidth}px`;
      indicator.style.transform = `translateX(${active.offsetLeft}px)`;
    };
    positionIndicator();
    window.addEventListener("resize", positionIndicator);
    return () => window.removeEventListener("resize", positionIndicator);
  }, [kind, composerOpen, formStep]);

  useEffect(() => {
    if (!composerOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeComposer();
    };
    document.addEventListener("keydown", onKey);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const timer = window.setTimeout(() => amountInputRef.current?.focus(), 60);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [composerOpen]);

  if (loading && transactions.length === 0) return <MovementsSkeleton />;

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
      {!composerOpen && error && <p className="error">{error}</p>}

      <div className="movement-composer-launch">
        <button
          type="button"
          className="btn secondary"
          onClick={() => setTaxonomyOpen(true)}
        >
          <Tags size={18} aria-hidden="true" /> Categorie e tag
        </button>
        <button type="button" className="btn" onClick={openNewMovement}>
          <Plus size={18} aria-hidden="true" /> Nuovo movimento
        </button>
      </div>

      {composerOpen && (
        <div
          className="movement-wizard-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) closeComposer();
          }}
        >
          <div
            className="movement-wizard"
            role="dialog"
            aria-modal="true"
            aria-labelledby="movement-wizard-title"
            ref={formRef}
          >
            <div className="movement-wizard-head">
              <div>
                <p className="eyebrow">{editingId ? "Modifica" : "Registro"}</p>
                <h2 id="movement-wizard-title">
                  {editingId ? "Modifica movimento" : "Nuovo movimento"}
                </h2>
              </div>
              <button
                type="button"
                className="icon-button"
                aria-label="Chiudi"
                onClick={closeComposer}
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="wizard-form">
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <div className="wizard-layout" ref={wizardLayoutRef}>
                <div className="wizard-main">
                  {formStep === 0 && (
                    <section className="wizard-step wizard-step-amount" aria-label="Importo">
                      <div
                        className="wizard-type"
                        role="group"
                        aria-label="Tipo di movimento"
                        ref={typePillRef}
                      >
                        <span
                          className="wizard-type-indicator"
                          ref={typeIndicatorRef}
                          aria-hidden="true"
                        />
                        {([
                          ["expense", "Spesa"],
                          ["income", "Entrata"],
                          ["transfer", "Trasferimento"],
                        ] as const).map(([value, label]) => (
                          <button
                            key={value}
                            type="button"
                            className={kind === value ? "active" : ""}
                            aria-pressed={kind === value}
                            onClick={() => setKind(value)}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                      <div className="wizard-amount-row">
                        <button
                          type="button"
                          className="wizard-round"
                          aria-label="Diminuisci di 50 centesimi"
                          onClick={() => setAmountValue(numberAmount() - 0.5)}
                        >
                          −
                        </button>
                        <span className="wizard-amount-shell">
                          <input
                            ref={amountInputRef}
                            className="wizard-amount-input"
                            type="text"
                            inputMode="decimal"
                            aria-label="Importo"
                            value={amount}
                            onChange={(event) => setAmount(sanitizeAmount(event.target.value))}
                          />
                          <span className="wizard-amount-suffix" aria-hidden="true">€</span>
                        </span>
                        <button
                          type="button"
                          className="wizard-round"
                          aria-label="Aumenta di 50 centesimi"
                          onClick={() => setAmountValue(numberAmount() + 0.5)}
                        >
                          +
                        </button>
                      </div>
                      <div className="wizard-slider">
                        <div className="wizard-ticks" aria-hidden="true">
                          {Array.from({ length: 21 }, (_, index) => (
                            <i
                              key={index}
                              className={`${index % 5 === 0 ? "major" : ""}${
                                Math.round(amountForSlider / 5) === index ? " active" : ""
                              }`}
                            />
                          ))}
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="100"
                          step="0.5"
                          value={amountForSlider}
                          aria-label="Importo da 0 a 100 euro, scatti di 50 centesimi"
                          onChange={(event) => setAmountValue(Number(event.target.value))}
                        />
                        <div className="wizard-ticks-labels">
                          <span>0 €</span>
                          <span>50 €</span>
                          <span>100 €</span>
                        </div>
                      </div>
                      {kind === "income" && (
                        <label className="wizard-field">
                          <span>Conto</span>
                          <AppSelect
                            options={accountOptions}
                            value={accountId}
                            onChange={setAccountId}
                            ariaLabel="Conto dell'entrata"
                            placeholder="Seleziona conto…"
                          />
                        </label>
                      )}
                      {kind === "expense" && (
                        <div className="wizard-fields">
                          <div className="wizard-source-toggle" role="group" aria-label="Pagato da">
                            <button
                              type="button"
                              className={expenseSource === "account" ? "active" : ""}
                              aria-pressed={expenseSource === "account"}
                              onClick={() => setExpenseSource("account")}
                            >
                              Conto
                            </button>
                            <button
                              type="button"
                              className={expenseSource === "savings" ? "active" : ""}
                              aria-pressed={expenseSource === "savings"}
                              onClick={() => setExpenseSource("savings")}
                            >
                              Salvadanaio
                            </button>
                          </div>
                          <label className="wizard-field">
                            <span>{expenseSource === "account" ? "Conto" : "Salvadanaio"}</span>
                            {expenseSource === "account" ? (
                              <AppSelect
                                options={accountOptions}
                                value={accountId}
                                onChange={setAccountId}
                                ariaLabel="Conto della spesa"
                                placeholder="Seleziona conto…"
                              />
                            ) : (
                              <AppSelect
                                options={savingsOptions}
                                value={savingsId}
                                onChange={setSavingsId}
                                ariaLabel="Salvadanaio della spesa"
                                placeholder="Seleziona salvadanaio…"
                              />
                            )}
                          </label>
                          {expenseSource === "savings" && (
                            <label className="wizard-checkbox">
                              <input
                                type="checkbox"
                                checked={confirmCoverage}
                                onChange={(event) => setConfirmCoverage(event.target.checked)}
                              />
                              <span className="wizard-checkbox-box" aria-hidden="true">
                                <Check size={14} aria-hidden="true" />
                              </span>
                              <span>Se il salvadanaio non basta, usa il conto di appoggio</span>
                            </label>
                          )}
                        </div>
                      )}
                      {kind === "transfer" && (
                        <div className="wizard-transfer">
                          <div className="wizard-fields">
                            <div className="wizard-source-toggle" role="group" aria-label="Origine">
                              <button
                                type="button"
                                className={fromKind === "account" ? "active" : ""}
                                aria-pressed={fromKind === "account"}
                                onClick={() => setFromKind("account")}
                              >
                                Conto
                              </button>
                              <button
                                type="button"
                                className={fromKind === "savings" ? "active" : ""}
                                aria-pressed={fromKind === "savings"}
                                onClick={() => setFromKind("savings")}
                              >
                                Salvadanaio
                              </button>
                            </div>
                            <label className="wizard-field">
                              <span>Da</span>
                              {fromKind === "account" ? (
                                <AppSelect
                                  options={accountOptions}
                                  value={fromAccountId}
                                  onChange={setFromAccountId}
                                  ariaLabel="Conto di origine"
                                  placeholder="Seleziona conto…"
                                />
                              ) : (
                                <AppSelect
                                  options={savingsOptions}
                                  value={fromSavingsId}
                                  onChange={setFromSavingsId}
                                  ariaLabel="Salvadanaio di origine"
                                  placeholder="Seleziona salvadanaio…"
                                />
                              )}
                            </label>
                          </div>
                          <div className="wizard-fields">
                            <div className="wizard-source-toggle" role="group" aria-label="Destinazione">
                              <button
                                type="button"
                                className={toKind === "account" ? "active" : ""}
                                aria-pressed={toKind === "account"}
                                onClick={() => setToKind("account")}
                              >
                                Conto
                              </button>
                              <button
                                type="button"
                                className={toKind === "savings" ? "active" : ""}
                                aria-pressed={toKind === "savings"}
                                onClick={() => setToKind("savings")}
                              >
                                Salvadanaio
                              </button>
                            </div>
                            <label className="wizard-field">
                              <span>A</span>
                              {toKind === "account" ? (
                                <AppSelect
                                  options={accountOptions}
                                  value={toAccountId}
                                  onChange={setToAccountId}
                                  ariaLabel="Conto di destinazione"
                                  placeholder="Seleziona conto…"
                                />
                              ) : (
                                <AppSelect
                                  options={savingsOptions}
                                  value={toSavingsId}
                                  onChange={setToSavingsId}
                                  ariaLabel="Salvadanaio di destinazione"
                                  placeholder="Seleziona salvadanaio…"
                                />
                              )}
                            </label>
                          </div>
                        </div>
                      )}
                    </section>
                  )}

                  {formStep === 1 && (
                    <section className="wizard-step" aria-label="Dettagli">
                      <label className="wizard-field">
                        <span>Descrizione</span>
                        <input
                          value={description}
                          onChange={(event) => setDescription(event.target.value)}
                          onBlur={(event) => void suggestForDescription(event.target.value)}
                          placeholder="Facoltativa"
                        />
                      </label>
                      <div className="wizard-field">
                        <span>Categoria</span>
                        <div
                          className="wizard-cat-pills"
                          role="group"
                          aria-label="Categorie"
                        >
                          <button
                            type="button"
                            className={`wizard-cat-pill${categoryId === "" ? " active" : ""}`}
                            aria-pressed={categoryId === ""}
                            onClick={() => {
                              setCategoryId("");
                              setSuggestion(null);
                            }}
                          >
                            <CategoryIcon name="tag" size={14} />
                            Altro (automatica)
                          </button>
                          {categories.map((category) => (
                            <button
                              key={category.id}
                              type="button"
                              className={`wizard-cat-pill${
                                String(category.id) === categoryId ? " active" : ""
                              }`}
                              aria-pressed={String(category.id) === categoryId}
                              onClick={() => {
                                setCategoryId(String(category.id));
                                setSuggestion(null);
                              }}
                            >
                              <CategoryIcon name={category.icon} size={14} />
                              {category.name}
                            </button>
                          ))}
                        </div>
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
                    </section>
                  )}

                  {formStep === 2 && (
                    <section className="wizard-step" aria-label="Data, ora e tag">
                      <h3 className="wizard-step-title">Data e ora e tag</h3>
                      <div className="wizard-datetime">
                        <DateField value={date} onChange={setDate} />
                        <TimeField value={time} onChange={setTime} />
                      </div>
                      <label className="wizard-field">
                        <span>Tag</span>
                        <input
                          value={tagInput}
                          onChange={(event) => setTagInput(event.target.value)}
                          placeholder="Separati da virgola"
                        />
                      </label>
                      {allTags.length > 0 && (
                        <div className="wizard-tag-pills" aria-label="Tag recenti">
                          {allTags.slice(0, 10).map((tag) => {
                            const active = summaryTags.includes(tag.name);
                            return (
                              <button
                                key={tag.id}
                                type="button"
                                className={`wizard-tag-pill${active ? " active" : ""}`}
                                aria-pressed={active}
                                onClick={() => toggleSummaryTag(tag.name)}
                              >
                                {tag.name}
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </section>
                  )}
                </div>

                <aside className="wizard-summary" aria-label="Riepilogo movimento">
                  <h3>Riepilogo</h3>
                  <div className="wizard-sum-line">
                    <span>Tipo</span>
                    <strong>{kindLabel}</strong>
                  </div>
                  <div className="wizard-sum-line">
                    <span>Fonte</span>
                    <strong>{sourceLabel()}</strong>
                  </div>
                  {formStep >= 1 && (
                    <>
                      <div className="wizard-sum-line">
                        <span>Descrizione</span>
                        <strong>{description || "—"}</strong>
                      </div>
                      <div className="wizard-sum-line">
                        <span>Categoria</span>
                        <strong>{categoryLabel()}</strong>
                      </div>
                    </>
                  )}
                  {formStep >= 2 && (
                    <>
                      <div className="wizard-sum-line">
                        <span>Data e ora</span>
                        <strong>{summaryDate} · {time}</strong>
                      </div>
                      <div className="wizard-sum-line">
                        <span>Tag</span>
                        <strong>{summaryTags.length > 0 ? summaryTags.join(", ") : "—"}</strong>
                      </div>
                    </>
                  )}
                  <div className="wizard-sum-total">
                    <span>Totale</span>
                    <strong>{money(numberAmount())}</strong>
                  </div>
                </aside>
              </div>

              <div className="wizard-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={formStep === 0 ? closeComposer : previousStep}
                >
                  {formStep === 0 ? "Annulla" : "Indietro"}
                </button>
                {formStep < 2 ? (
                  <button type="button" onClick={nextStep}>
                    Avanti
                  </button>
                ) : (
                  <button type="submit" disabled={busy || !confirmReady}>
                    {busy ? "Registrazione…" : editingId ? "Salva modifiche" : "Conferma"}
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}

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
