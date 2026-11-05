import { useCallback, useEffect, useState, type FormEvent } from "react";
import { api, type Account, type AccountType } from "../api";
import { ConfirmModal } from "../components/ConfirmModal";
import { LoadingScreen } from "../components/Guards";
import { useToast } from "../components/Toast";
import { amountClass, money } from "../format";

const TYPES: { value: AccountType; label: string }[] = [
  { value: "cash", label: "Contanti" },
  { value: "checking", label: "Conto corrente" },
  { value: "card", label: "Carta" },
  { value: "other", label: "Altro" },
];

export function AccountsPage() {
  const { notify } = useToast();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [name, setName] = useState("");
  const [type, setType] = useState<AccountType>("cash");
  const [initialBalance, setInitialBalance] = useState("0.00");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Account | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.accounts();
      setAccounts(data.accounts);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.createAccount({ name, type, initial_balance: initialBalance });
      setName("");
      setType("cash");
      setInitialBalance("0.00");
      setMessage("Conto creato.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleArchive(account: Account) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.updateAccount(account.id, { archived: !account.archived });
      setMessage(account.archived ? "Conto riattivato." : "Conto archiviato.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(account: Account) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.deleteAccount(account.id);
      notify(`Conto «${account.name}» eliminato.`, {
        label: "Annulla",
        onClick: () => {
          api
            .restoreTrash("account", account.id)
            .then(() => load())
            .catch((err) =>
              setError(err instanceof Error ? err.message : "Ripristino non riuscito."),
            );
        },
      });
      setConfirmDelete(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eliminazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingScreen />;

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Patrimonio</p>
          <h1>Conti</h1>
        </div>
      </section>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="two-columns">
        <section className="card">
          <h2>Nuovo conto</h2>
          <form onSubmit={handleCreate} className="stack">
            <label>
              Nome
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="Contanti, Carta 1, Banca…"
                required
              />
            </label>
            <label>
              Tipo
              <select
                value={type}
                onChange={(event) => setType(event.target.value as AccountType)}
              >
                {TYPES.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Saldo iniziale
              <input
                type="number"
                step="0.01"
                value={initialBalance}
                onChange={(event) => setInitialBalance(event.target.value)}
              />
            </label>
            <p className="muted small">
              Se diverso da zero, il saldo iniziale diventa un movimento di
              apertura.
            </p>
            <button type="submit" disabled={busy}>
              {busy ? "Creazione…" : "Crea conto"}
            </button>
          </form>
        </section>

        <section className="card">
          <h2>I tuoi conti ({accounts.length})</h2>
          {accounts.length === 0 ? (
            <p className="muted">Nessun conto creato.</p>
          ) : (
            <ul className="entity-list">
              {accounts.map((account) => (
                <li key={account.id} className={account.archived ? "archived" : ""}>
                  <div>
                    <strong>{account.name}</strong>
                    <span className="muted small">
                      {" "}
                      · {account.type_label}
                      {account.archived ? " · archiviato" : ""}
                    </span>
                  </div>
                  <div className="entity-side">
                    <span className={amountClass(account.balance)}>
                      {money(account.balance)}
                    </span>
                    <div className="actions">
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => void toggleArchive(account)}
                        disabled={busy}
                      >
                        {account.archived ? "Riattiva" : "Archivia"}
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => setConfirmDelete(account)}
                        disabled={busy}
                      >
                        Elimina
                      </button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
      {confirmDelete && (
        <ConfirmModal
          title={`Eliminare il conto «${confirmDelete.name}»?`}
          summary={[
            `Saldo attuale: ${money(confirmDelete.balance)}.`,
            "Possibile solo senza movimenti (altrimenti archivia).",
            "Il conto finisce nel cestino per 30 giorni e non incide più sui saldi.",
          ]}
          busy={busy}
          onConfirm={() => void remove(confirmDelete)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  );
}
