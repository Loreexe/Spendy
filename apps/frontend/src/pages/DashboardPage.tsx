import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Dashboard, type Line, type Transaction } from "../api";
import { useAuth } from "../auth";
import { LoadingScreen } from "../components/Guards";
import {
  amountClass,
  firstOfMonthISO,
  isoDate,
  money,
  signedMoney,
  todayISO,
} from "../format";

function lineLabel(line: Line): string {
  const target = line.account_name ?? line.savings_name ?? "—";
  const role =
    line.role === "technical"
      ? " (tecnico)"
      : line.role === "transfer_out"
        ? " (uscita)"
        : line.role === "transfer_in"
          ? " (entrata)"
          : "";
  return `${target}${role}`;
}

function TransactionRows({ transaction }: { transaction: Transaction }) {
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
    </li>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [start, setStart] = useState(firstOfMonthISO());
  const [end, setEnd] = useState(todayISO());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (from: string, to: string) => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.dashboard(from, to));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user && !user.is_global_admin) {
      void load(start, end);
    } else {
      setLoading(false);
    }
  }, [load, start, end, user]);

  function applyPreset(from: string, to: string) {
    setStart(from);
    setEnd(to);
  }

  function previousMonth() {
    const now = new Date();
    const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const to = new Date(now.getFullYear(), now.getMonth(), 0);
    applyPreset(isoDate(from), isoDate(to));
  }

  if (!user) return null;

  if (user.is_global_admin) {
    return (
      <div className="card">
        <p className="eyebrow">Amministrazione</p>
        <h1>Nessun profilo finanziario</h1>
        <p className="muted">
          L'amministratore globale gestisce account e impostazioni, ma non ha
          conti, movimenti o salvadanai.
        </p>
        <Link className="button" to="/admin">
          Vai all'amministrazione
        </Link>
      </div>
    );
  }

  if (loading && !data) return <LoadingScreen />;

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>Le tue finanze</h1>
        </div>
        <div className="period-controls">
          <button type="button" className="secondary" onClick={() => applyPreset(firstOfMonthISO(), todayISO())}>
            Mese corrente
          </button>
          <button type="button" className="secondary" onClick={previousMonth}>
            Mese precedente
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              applyPreset(
                `${new Date().getFullYear()}-01-01`,
                todayISO(),
              )
            }
          >
            Anno corrente
          </button>
          <button type="button" className="secondary" onClick={() => applyPreset("2000-01-01", todayISO())}>
            Tutto
          </button>
        </div>
      </section>

      <section className="period-bar card">
        <label>
          Dal
          <input type="date" value={start} onChange={(event) => setStart(event.target.value)} />
        </label>
        <label>
          Al
          <input type="date" value={end} onChange={(event) => setEnd(event.target.value)} />
        </label>
        <button type="button" onClick={() => void load(start, end)}>
          Applica
        </button>
      </section>

      {error && <p className="error">{error}</p>}

      {data && (
        <>
          <section className="stat-grid">
            <div className="card stat">
              <span className="stat-label">Saldo totale</span>
              <strong className={amountClass(data.total_balance)}>
                {money(data.total_balance)}
              </strong>
              <span className="muted small">Solo conti personali</span>
            </div>
            <div className="card stat">
              <span className="stat-label">Patrimonio</span>
              <strong>{money(data.total_patrimony)}</strong>
              <span className="muted small">Conti + salvadanai</span>
            </div>
            <div className="card stat">
              <span className="stat-label">Salvadanai</span>
              <strong>{money(data.total_savings)}</strong>
              <span className="muted small">Accantonamenti</span>
            </div>
            <div className="card stat">
              <span className="stat-label">Saldo del periodo</span>
              <strong className={amountClass(data.period_balance)}>
                {money(data.period_balance)}
              </strong>
              <span className="muted small">
                {new Date(`${data.period.start}T12:00:00`).toLocaleDateString("it-IT")} –{" "}
                {new Date(`${data.period.end}T12:00:00`).toLocaleDateString("it-IT")}
              </span>
            </div>
          </section>

          <section className="two-columns">
            <div className="card">
              <div className="card-heading">
                <h2>Conti</h2>
                <Link to="/accounts">Gestisci</Link>
              </div>
              {data.accounts.length === 0 ? (
                <p className="muted">Nessun conto. Creane uno per iniziare.</p>
              ) : (
                <ul className="balance-list">
                  {data.accounts.map((account) => (
                    <li key={account.id}>
                      <div>
                        <strong>{account.name}</strong>
                        <span className="muted small">
                          {" "}
                          · {account.type_label}
                          {account.archived ? " · archiviato" : ""}
                        </span>
                      </div>
                      <span className={amountClass(account.balance)}>
                        {money(account.balance)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="card">
              <div className="card-heading">
                <h2>Salvadanai</h2>
                <Link to="/savings">Gestisci</Link>
              </div>
              {data.savings.length === 0 ? (
                <p className="muted">Nessun salvadanaio.</p>
              ) : (
                <ul className="balance-list">
                  {data.savings.map((savings) => (
                    <li key={savings.id}>
                      <div>
                        <strong>{savings.name}</strong>
                        <span className="muted small">
                          {" "}
                          · appoggio {savings.backing_account_name}
                        </span>
                      </div>
                      <span className={amountClass(savings.balance)}>
                        {money(savings.balance)}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="card">
            <div className="card-heading">
              <h2>Ultimi movimenti</h2>
              <Link to="/movements">Tutti i movimenti</Link>
            </div>
            {data.recent_transactions.length === 0 ? (
              <p className="muted">Nessun movimento registrato.</p>
            ) : (
              <ul className="movement-list">
                {data.recent_transactions.map((transaction) => (
                  <TransactionRows key={transaction.id} transaction={transaction} />
                ))}
              </ul>
            )}
          </section>

          <section className="stat-grid compact">
            <div className="card stat">
              <span className="stat-label">Entrate del periodo</span>
              <strong className="positive">{money(data.income_total)}</strong>
            </div>
            <div className="card stat">
              <span className="stat-label">Uscite del periodo</span>
              <strong className="negative">{money(data.expense_total)}</strong>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
