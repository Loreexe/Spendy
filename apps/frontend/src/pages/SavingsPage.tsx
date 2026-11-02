import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  type Account,
  type SavingsAccount,
} from "../api";
import { LoadingScreen } from "../components/Guards";
import { amountClass, money, todayISO } from "../format";

function SavingsCard({
  savings,
  accounts,
  onChanged,
  report,
}: {
  savings: SavingsAccount;
  accounts: Account[];
  onChanged: () => Promise<void>;
  report: (message: string | null, error: string | null) => void;
}) {
  const [direction, setDirection] = useState<"in" | "out">("in");
  const [accountId, setAccountId] = useState(
    String(savings.backing_account ?? accounts[0]?.id ?? ""),
  );
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!accountId && accounts[0]) setAccountId(String(accounts[0].id));
  }, [accountId, accounts]);

  async function operate(event: FormEvent) {
    event.preventDefault();
    if (!accountId) {
      report(null, "Serve un conto per il versamento o prelievo.");
      return;
    }
    setBusy(true);
    report(null, null);
    try {
      await api.createTransaction(
        direction === "in"
          ? {
              kind: "transfer",
              date: todayISO(),
              description: `Versamento su ${savings.name}`,
              amount,
              from_account: Number(accountId),
              to_savings: savings.id,
            }
          : {
              kind: "transfer",
              date: todayISO(),
              description: `Prelievo da ${savings.name}`,
              amount,
              from_savings: savings.id,
              to_account: Number(accountId),
            },
      );
      setAmount("");
      await onChanged();
      report(
        direction === "in" ? "Versamento registrato." : "Prelievo registrato.",
        null,
      );
    } catch (err) {
      report(null, err instanceof Error ? err.message : "Operazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm(`Eliminare il salvadanaio "${savings.name}"?`)) return;
    setBusy(true);
    report(null, null);
    try {
      await api.deleteSavings(savings.id);
      await onChanged();
      report("Salvadanaio eliminato; il saldo residuo è stato trasferito.", null);
    } catch (err) {
      report(null, err instanceof Error ? err.message : "Eliminazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="entity-card">
      <div className="entity-card-head">
        <div>
          <strong>{savings.name}</strong>
          <span className="muted small">
            {" "}
            · appoggio {savings.backing_account_name}
          </span>
        </div>
        <span className={`money ${amountClass(savings.balance)}`}>
          {money(savings.balance)}
        </span>
      </div>
      <form onSubmit={operate} className="inline-form">
        <select
          value={direction}
          onChange={(event) => setDirection(event.target.value as "in" | "out")}
        >
          <option value="in">Versamento</option>
          <option value="out">Prelievo</option>
        </select>
        <select
          value={accountId}
          onChange={(event) => setAccountId(event.target.value)}
          required
        >
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name}
            </option>
          ))}
        </select>
        <input
          type="number"
          step="0.01"
          min="0.01"
          placeholder="Importo"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
          required
        />
        <button type="submit" disabled={busy}>
          Registra
        </button>
        <button
          type="button"
          className="danger"
          onClick={() => void remove()}
          disabled={busy}
        >
          Elimina
        </button>
      </form>
    </li>
  );
}

export function SavingsPage() {
  const [savings, setSavings] = useState<SavingsAccount[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [name, setName] = useState("");
  const [backingAccount, setBackingAccount] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [savingsData, accountsData] = await Promise.all([
        api.savings(),
        api.accounts(),
      ]);
      setSavings(savingsData.savings);
      const active = accountsData.accounts.filter((account) => !account.archived);
      setAccounts(active);
      if (!backingAccount && active[0]) {
        setBackingAccount(String(active[0].id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, [backingAccount]);

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.createSavings({
        name,
        backing_account: Number(backingAccount),
      });
      setName("");
      setMessage("Salvadanaio creato.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingScreen />;

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Accantonamenti</p>
          <h1>Salvadanai</h1>
        </div>
      </section>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="two-columns">
        <section className="card">
          <h2>Nuovo salvadanaio</h2>
          {accounts.length === 0 ? (
            <p className="muted">
              Crea prima un conto: serve come conto di appoggio.
            </p>
          ) : (
            <form onSubmit={handleCreate} className="stack">
              <label>
                Nome
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Salute, Vacanze…"
                  required
                />
              </label>
              <label>
                Conto di appoggio
                <select
                  value={backingAccount}
                  onChange={(event) => setBackingAccount(event.target.value)}
                  required
                >
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </label>
              <p className="muted small">
                Il conto di appoggio non è modificabile in questa versione.
              </p>
              <button type="submit" disabled={busy}>
                {busy ? "Creazione…" : "Crea salvadanaio"}
              </button>
            </form>
          )}
        </section>

        <section className="card">
          <h2>I tuoi salvadanai ({savings.length})</h2>
          {savings.length === 0 ? (
            <p className="muted">Nessun salvadanaio creato.</p>
          ) : (
            <ul className="entity-list">
              {savings.map((item) => (
                <SavingsCard
                  key={item.id}
                  savings={item}
                  accounts={accounts}
                  onChanged={load}
                  report={(nextMessage, nextError) => {
                    setMessage(nextMessage);
                    setError(nextError);
                  }}
                />
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
