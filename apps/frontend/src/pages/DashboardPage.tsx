import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  api,
  type Dashboard,
  type DashboardSeries,
  type Line,
  type Transaction,
} from "../api";
import { useAuth } from "../auth";
import { AccountsMenu } from "../components/AccountsMenu";
import { CategoryBars, InOutBars, TrendChart } from "../components/Charts";
import { EmptyState } from "../components/EmptyState";
import { DashboardContentSkeleton } from "../components/HomeSkeleton";
import { MovementKindIcon, TransactionIcon } from "../components/TransactionIcon";
import {
  amountClass,
  firstOfMonthISO,
  formatDate,
  isoDate,
  money,
  normalizeTime,
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

const MINUS = "\u2212";

/**
 * Importo della riga compatta: segno e colore per direzione, la stessa
 * convenzione del client Android (spese con «−» e `--down`, entrate con «+»
 * e `--up`, trasferimenti neutri). L'aggregato `amount` dell'API è positivo
 * per ogni tipo: il segno va ricavato da `kind`.
 */
function compactAmount(transaction: Transaction): {
  text: string;
  className: string;
} {
  const magnitude = Math.abs(Number(transaction.amount));
  if (transaction.kind === "expense") {
    return { text: `${MINUS}${money(magnitude)}`, className: "money negative" };
  }
  if (transaction.kind === "income") {
    return { text: `+${money(magnitude)}`, className: "money positive" };
  }
  return { text: money(magnitude), className: "money" };
}

function TransactionRows({
  transaction,
  compact = false,
}: {
  transaction: Transaction;
  compact?: boolean;
}) {
  const time = normalizeTime(transaction.time);
  const amount = compact
    ? compactAmount(transaction)
    : {
        text: money(transaction.amount),
        className: `money ${amountClass(transaction.amount)}`,
      };
  return (
    <li className={`movement-row${compact ? " movement-row-compact" : ""}`}>
      <span className="movement-leading">
        <TransactionIcon transaction={transaction} size={compact ? 24 : 20} />
      </span>
      <div className="movement-main">
        <div className="movement-title">
          <strong>{transaction.description || transaction.kind_label}</strong>
          <span className={amount.className}>{amount.text}</span>
          {compact && (
            <span className="movement-kind" title={transaction.kind_label}>
              <MovementKindIcon kind={transaction.kind} />
            </span>
          )}
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
        {!compact && (
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
        )}
      </div>
    </li>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState<Dashboard | null>(null);
  const [series, setSeries] = useState<DashboardSeries | null>(null);
  const [start, setStart] = useState(firstOfMonthISO());
  const [end, setEnd] = useState(todayISO());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (from: string, to: string) => {
    setLoading(true);
    setError(null);
    try {
      const [dashboardData, seriesData] = await Promise.all([
        api.dashboard(from, to),
        api.dashboardSeries(from, to),
      ]);
      setData(dashboardData);
      setSeries(seriesData);
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

  function previousMonthData() {
    const now = new Date();
    const from = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const to = new Date(now.getFullYear(), now.getMonth(), 0);
    return [isoDate(from), isoDate(to)] as const;
  }

  const [prevFrom, prevTo] = previousMonthData();
  const presets = [
    { key: "current", label: "Mese corrente", from: firstOfMonthISO(), to: todayISO() },
    { key: "previous", label: "Mese precedente", from: prevFrom, to: prevTo },
    {
      key: "year",
      label: "Anno corrente",
      from: `${new Date().getFullYear()}-01-01`,
      to: todayISO(),
    },
    { key: "all", label: "Tutto", from: "2000-01-01", to: todayISO() },
  ];
  const activeIndex = presets.findIndex(
    (preset) => start === preset.from && end === preset.to,
  );

  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const segmentedRef = useRef<HTMLDivElement | null>(null);
  const [indicator, setIndicator] = useState({
    left: 0,
    width: 0,
    visible: false,
  });

  useLayoutEffect(() => {
    const measure = () => {
      const el = buttonRefs.current[activeIndex];
      if (!el || activeIndex < 0) {
        setIndicator((current) => ({ ...current, visible: false }));
        return;
      }
      setIndicator({
        left: el.offsetLeft,
        width: el.offsetWidth,
        visible: true,
      });
    };
    measure();
    const observer = new ResizeObserver(measure);
    if (segmentedRef.current) observer.observe(segmentedRef.current);
    window.addEventListener("resize", measure);
    return () => {
      observer.disconnect();
      window.removeEventListener("resize", measure);
    };
  }, [activeIndex, loading, user]);

  if (!user) return null;

  if (user.is_global_admin) {
    return (
      <div className="card">
        <p className="eyebrow">Home</p>
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

  const hasTrend = (series?.buckets.length ?? 0) >= 2;
  const hasFlow = Boolean(
    data && (Number(data.income_total) > 0 || Number(data.expense_total) > 0),
  );
  const hasCategories = (series?.by_category.length ?? 0) > 0;
  const showCharts = hasTrend || hasFlow || hasCategories;

  return (
    <div className="stack-page dashboard-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Home</p>
          <h1>Le tue finanze</h1>
        </div>
      </section>

      <section className="dash-toolbar">
        <div
          className="period-segmented"
          role="group"
          aria-label="Periodo rapido"
          ref={segmentedRef}
        >
          <span
            className={`preset-indicator${indicator.visible ? "" : " hidden"}`}
            style={{
              width: `${indicator.width}px`,
              transform: `translateX(${indicator.left}px)`,
            }}
            aria-hidden="true"
          />
          {presets.map((preset, index) => (
            <button
              key={preset.key}
              type="button"
              ref={(el) => {
                buttonRefs.current[index] = el;
              }}
              aria-pressed={start === preset.from && end === preset.to}
              className={
                start === preset.from && end === preset.to ? "active" : ""
              }
              onClick={() => applyPreset(preset.from, preset.to)}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <div className="dash-range">
          <label>
            <span>Dal</span>
            <input
              type="date"
              aria-label="Data iniziale"
              value={start}
              onChange={(event) => setStart(event.target.value)}
            />
          </label>
          <span className="dash-range-sep" aria-hidden="true">
            →
          </span>
          <label>
            <span>Al</span>
            <input
              type="date"
              aria-label="Data finale"
              value={end}
              onChange={(event) => setEnd(event.target.value)}
            />
          </label>
          <button
            type="button"
            className="secondary dash-apply"
            onClick={() => void load(start, end)}
          >
            Applica
          </button>
        </div>
      </section>

      <div
        className={`dash-content${loading && data ? " is-updating" : ""}`}
        aria-busy={loading || undefined}
      >
        <span className="visually-hidden" role="status">
          {loading && data ? "Aggiornamento del periodo in corso…" : ""}
        </span>
        {error && (
          <div className="error error-stack" role="alert">
            <span>{error}</span>
            {data && (
              <span className="muted small">
                I dati mostrati sono quelli dell'ultimo caricamento riuscito.
              </span>
            )}
            <button
              type="button"
              className="secondary small-button"
              onClick={() => void load(start, end)}
            >
              Riprova
            </button>
          </div>
        )}
        {loading && !data ? (
          <DashboardContentSkeleton />
        ) : data ? (
          <>
            <section className="dash-summary">
              <div className="card dash-hero">
                <div className="dash-hero-head">
                  <span className="stat-label">Saldo del periodo</span>
                  <AccountsMenu accounts={data.accounts} />
                </div>
                <strong className="dash-big">
                  {money(data.period_balance)}
                </strong>
                <p className="muted small">
                  {formatDate(data.period.start)} – {formatDate(data.period.end)} ·
                  Entrate − Uscite
                  {Number(data.period_dividends) > 0
                    ? ` · dividendi ${money(data.period_dividends)}`
                    : ""}
                </p>
                <div className="dash-breakdown">
                  <div>
                    <span>Saldo conti</span>
                    <strong>{money(data.total_balance)}</strong>
                  </div>
                  <div>
                    <span>Salvadanai</span>
                    <strong>{money(data.total_savings)}</strong>
                  </div>
                  <div>
                    <span>Investimenti</span>
                    <strong>{money(data.total_investments_cost)}</strong>
                    <span className="muted small">
                      valore {money(data.total_investments_value)}
                      {data.positions_without_price > 0
                        ? ` · ${data.positions_without_price} senza prezzo`
                        : ""}
                    </span>
                  </div>
                  <div>
                    <span>Patrimonio</span>
                    <strong>{money(data.total_patrimony)}</strong>
                  </div>
                </div>
              </div>
            </section>

            {showCharts && (
              <section className="card dash-charts">
                <div className="card-heading">
                  <h2>Grafici del periodo</h2>
                </div>
                <div className="stack">
                  {hasTrend && (
                    <div>
                      <h3 className="stat-label">
                        Andamento saldo e patrimonio
                      </h3>
                      <TrendChart points={series?.buckets ?? []} />
                    </div>
                  )}
                  {(hasFlow || hasCategories) && (
                    <div
                      className={`dash-charts-row${hasFlow && hasCategories ? "" : " single"}`}
                    >
                      {hasFlow && (
                        <div>
                          <h3 className="stat-label">Entrate vs uscite</h3>
                          <InOutBars
                            income={data.income_total}
                            expense={data.expense_total}
                          />
                        </div>
                      )}
                      {hasCategories && (
                        <div>
                          <h3 className="stat-label">Spese per categoria</h3>
                          <CategoryBars rows={series?.by_category ?? []} />
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </section>
            )}

            <section className="two-columns equal">
              <div className="card">
                <div className="card-heading">
                  <h2>Conti</h2>
                  {data.accounts.length > 0 && (
                    <Link to="/accounts">Gestisci</Link>
                  )}
                </div>
                {data.accounts.length === 0 ? (
                  <EmptyState
                    illustration="accounts"
                    title="Nessun conto"
                    description="Aggiungi il primo conto per iniziare a tenere traccia di saldi e movimenti."
                    actionLabel="Crea conto"
                    onAction={() => navigate("/accounts")}
                  />
                ) : (
                  <>
                    <p className="muted small dash-note">
                      Saldo del periodo; tra parentesi il saldo attuale con i
                      salvadanai.
                    </p>
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
                        <span className="account-amounts">
                          <span className={amountClass(account.period_balance ?? "0")}>
                            {money(account.period_balance ?? "0.00")}
                          </span>
                          <span className="muted small">
                            ({money(account.total_with_savings ?? account.balance)})
                          </span>
                        </span>
                      </li>
                    ))}
                  </ul>
                  </>
                )}
              </div>

              <div className="card">
                <div className="card-heading">
                  <h2>Salvadanai</h2>
                  {data.savings.length > 0 && (
                    <Link to="/savings">Gestisci</Link>
                  )}
                </div>
                {data.savings.length === 0 ? (
                  <EmptyState
                    illustration="savings"
                    title="Nessun salvadanaio"
                    description="Crea un salvadanaio per mettere da parte i risparmi."
                    actionLabel="Crea salvadanaio"
                    onAction={() => navigate("/savings")}
                  />
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
                {data.recent_transactions.length > 0 && (
                  <Link to="/movements">Tutti i movimenti</Link>
                )}
              </div>
              {data.recent_transactions.length === 0 ? (
                <EmptyState
                  illustration="movements"
                  title="Nessun movimento"
                  description="Registra il primo movimento per vedere qui gli ultimi aggiornamenti."
                  actionLabel="Registra movimento"
                  onAction={() => navigate("/movements")}
                />
              ) : (
                <ul className="movement-list">
                  {data.recent_transactions
                    .slice(0, 4)
                    .map((transaction) => (
                      <TransactionRows
                        key={transaction.id}
                        transaction={transaction}
                        compact
                      />
                    ))}
                </ul>
              )}
            </section>
          </>
        ) : null}
      </div>
    </div>
  );
}
