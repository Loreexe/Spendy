import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  type Account,
  type AutomationExecution,
  type AutomationExecutionStatus,
  type Automation,
  type AutomationIntervalUnit,
  type AutomationKind,
  type FinanceNotification,
  type SavingsAccount,
} from "../api";
import { LoadingScreen } from "../components/Guards";
import { useToast } from "../components/Toast";
import { money, todayISO } from "../format";

function prettyDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(`${value}T12:00:00`).toLocaleDateString("it-IT");
}

function executionBadge(status: AutomationExecutionStatus): string {
  if (status === "succeeded") return "ok";
  if (status === "pending") return "pending";
  if (status === "failed") return "rejected";
  return "disabled";
}


function AutomationEditForm({
  automation,
  busy,
  onSave,
}: {
  automation: Automation;
  busy: boolean;
  onSave: (data: {
    amount: string;
    description: string;
    interval_count: number;
    interval_unit: AutomationIntervalUnit;
    advance_notice_days: number;
    next_run_on: string;
  }) => void;
}) {
  const [amount, setAmount] = useState(automation.amount);
  const [description, setDescription] = useState(automation.description);
  const [intervalCount, setIntervalCount] = useState(
    String(automation.interval_count),
  );
  const [intervalUnit, setIntervalUnit] = useState(automation.interval_unit);
  const [noticeDays, setNoticeDays] = useState(
    String(automation.advance_notice_days),
  );
  const [nextRunOn, setNextRunOn] = useState(automation.next_run_on);

  return (
    <form
      className="inline-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave({
          amount,
          description,
          interval_count: Number(intervalCount),
          interval_unit: intervalUnit,
          advance_notice_days: Number(noticeDays),
          next_run_on: nextRunOn,
        });
      }}
    >
      {automation.kind === "expense" && (
        <input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Descrizione spesa"
          required
        />
      )}
      <input
        type="number"
        step="0.01"
        min="0.01"
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
        required
      />
      <input
        type="number"
        min="1"
        max="999"
        value={intervalCount}
        onChange={(event) => setIntervalCount(event.target.value)}
        title="Ogni quanti..."
        required
      />
      <select
        value={intervalUnit}
        onChange={(event) =>
          setIntervalUnit(event.target.value as AutomationIntervalUnit)
        }
      >
        <option value="day">giorni</option>
        <option value="week">settimane</option>
        <option value="month">mesi</option>
        <option value="year">anni</option>
      </select>
      <input
        type="number"
        min="0"
        max="30"
        value={noticeDays}
        onChange={(event) => setNoticeDays(event.target.value)}
        title="Giorni di preavviso (0 = disattivato)"
        required
      />
      <input
        type="date"
        value={nextRunOn}
        onChange={(event) => setNextRunOn(event.target.value)}
        required
      />
      <button type="submit" disabled={busy}>
        Salva
      </button>
    </form>
  );
}

export function AutomationsPage() {
  const { notify } = useToast();
  const [automations, setAutomations] = useState<Automation[]>([]);
  const [executions, setExecutions] = useState<AutomationExecution[]>([]);
  const [notifications, setNotifications] = useState<FinanceNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [savings, setSavings] = useState<SavingsAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [kind, setKind] = useState<AutomationKind>("expense");
  const [amount, setAmount] = useState("");
  const [description, setDescription] = useState("");
  const [intervalCount, setIntervalCount] = useState("1");
  const [intervalUnit, setIntervalUnit] =
    useState<AutomationIntervalUnit>("month");
  const [noticeDays, setNoticeDays] = useState("3");
  const [nextRunOn, setNextRunOn] = useState(todayISO());
  const [sourceAccount, setSourceAccount] = useState("");
  const [destination, setDestination] = useState("");
  const [selected, setSelected] = useState<Record<number, number[]>>({});

  const load = useCallback(async () => {
    try {
      const [
        automationData,
        executionData,
        notificationData,
        accountData,
        savingsData,
      ] = await Promise.all([
        api.automations(),
        api.automationExecutions({ limit: 100 }),
        api.notifications({ limit: 30 }),
        api.accounts(),
        api.savings(),
      ]);
      setAutomations(automationData.automations);
      setExecutions(executionData.executions);
      setNotifications(notificationData.notifications);
      setUnread(notificationData.unread_count);
      const activeAccounts = accountData.accounts.filter(
        (account) => !account.archived,
      );
      setAccounts(activeAccounts);
      setSavings(savingsData.savings);
      setSourceAccount((current) => current || String(activeAccounts[0]?.id ?? ""));
      setDestination((current) => current || String(savingsData.savings[0]?.id ?? ""));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Caricamento non riuscito.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const pendingByRule = executions.filter(
    (execution) => execution.status === "pending",
  );

  async function runAction(
    action: () => Promise<string | void>,
    fallback: string,
  ) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await action();
      await load();
      setMessage(typeof result === "string" ? result : fallback);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!sourceAccount) {
      setError("Serve un conto di partenza.");
      return;
    }
    if (kind === "transfer" && !destination) {
      setError("Serve un salvadanaio di destinazione.");
      return;
    }
    if (kind === "expense" && !description.trim()) {
      setError("Indica la descrizione della spesa.");
      return;
    }
    await runAction(
      async () => {
        await api.createAutomation({
          kind,
          source_account: Number(sourceAccount),
          amount,
          description: kind === "expense" ? description : "",
          interval_count: Number(intervalCount),
          interval_unit: intervalUnit,
          advance_notice_days: Number(noticeDays),
          next_run_on: nextRunOn,
          ...(kind === "transfer" ? { savings: Number(destination) } : {}),
        });
        setAmount("");
        setDescription("");
      },
      "Automazione creata.",
    );
  }

  async function toggleStatus(automation: Automation) {
    const next = automation.status === "active" ? "paused" : "active";
    await runAction(
      async () => {
        await api.updateAutomation(automation.id, { status: next });
      },
      next === "paused" ? "Automazione messa in pausa." : "Automazione riattivata.",
    );
  }

  async function runOne(automation: Automation) {
    await runAction(async () => {
      const result = await api.runAutomation(automation.id);
      return (
        `Esecuzione: ${result.outcome.executed} eseguite, ` +
        `${result.outcome.pending_choice} in attesa, ` +
        `${result.outcome.alerts} avvisi di saldo.`
      );
    }, "Automazione elaborata.");
  }

  async function resolve(
    automation: Automation,
    recover: number[],
  ) {
    await runAction(async () => {
      const result = await api.resolveAutomation(automation.id, recover);
      setSelected((current) => ({ ...current, [automation.id]: [] }));
      return (
        `Recuperate ${result.outcome.recovered}, ` +
        `saltate ${result.outcome.skipped}.`
      );
    }, "Scelta registrata.");
  }

  function toggleSelected(automationId: number, executionId: number) {
    setSelected((current) => {
      const chosen = current[automationId] ?? [];
      return {
        ...current,
        [automationId]: chosen.includes(executionId)
          ? chosen.filter((id) => id !== executionId)
          : [...chosen, executionId],
      };
    });
  }

  if (loading) return <LoadingScreen />;

  const activeAccounts = accounts;
  const hasDestinations = savings.length > 0;

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Accantonamenti ricorrenti</p>
          <h1>Automazioni</h1>
          <p className="muted">
            Spese ricorrenti e versamenti periodici verso i salvadanai, con
            recupero delle occorrenze perse e storico delle esecuzioni.
          </p>
        </div>
        <button
          type="button"
          className="secondary"
          disabled={busy}
          onClick={() =>
            void runAction(async () => {
              const result = await api.runAutomations();
              return (
                `Controllo completato: ${result.outcome.executed} eseguite, ` +
                `${result.outcome.pending_choice} in attesa, ` +
                `${result.outcome.alerts} avvisi di saldo.`
              );
            }, "Controllo completato.")
          }
        >
          Controlla scadenze
        </button>
      </section>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="two-columns">
        <section className="card">
          <h2>Nuova automazione</h2>
          {activeAccounts.length === 0 ? (
            <p className="muted">
              Serve almeno un conto attivo: crealo prima di impostare
              un'automazione.
            </p>
          ) : (
            <form onSubmit={handleCreate} className="stack">
              <label>
                Tipo
                <select
                  value={kind}
                  onChange={(event) =>
                    setKind(event.target.value as AutomationKind)
                  }
                >
                  <option value="expense">Spesa ricorrente</option>
                  <option value="transfer">Versamento su salvadanaio</option>
                </select>
              </label>
              {kind === "expense" ? (
                <label>
                  Descrizione
                  <input
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    placeholder="Netflix, affitto, palestra…"
                    required
                  />
                </label>
              ) : (
                <label>
                  Salvadanaio di destinazione
                  <select
                    value={destination}
                    onChange={(event) => setDestination(event.target.value)}
                    required
                  >
                    {savings.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name} · {money(item.balance)}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label>
                Importo
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="100,00"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  required
                />
              </label>
              <label>
                Periodicità
                <span className="inline-form">
                  <span className="muted">Ogni</span>
                  <input
                    type="number"
                    min="1"
                    max="999"
                    value={intervalCount}
                    onChange={(event) => setIntervalCount(event.target.value)}
                    required
                  />
                  <select
                    value={intervalUnit}
                    onChange={(event) =>
                      setIntervalUnit(
                        event.target.value as AutomationIntervalUnit,
                      )
                    }
                  >
                    <option value="day">giorni</option>
                    <option value="week">settimane</option>
                    <option value="month">mesi</option>
                    <option value="year">anni</option>
                  </select>
                </span>
              </label>
              <label>
                Avviso saldo insufficiente
                <span className="inline-form">
                  <input
                    type="number"
                    min="0"
                    max="30"
                    value={noticeDays}
                    onChange={(event) => setNoticeDays(event.target.value)}
                    required
                  />
                  <span className="muted">
                    giorni prima (0 = disattivato)
                  </span>
                </span>
              </label>
              <label>
                Prima esecuzione
                <input
                  type="date"
                  value={nextRunOn}
                  onChange={(event) => setNextRunOn(event.target.value)}
                  required
                />
              </label>
              <label>
                {kind === "expense" ? "Conto di addebito" : "Conto di partenza"}
                <select
                  value={sourceAccount}
                  onChange={(event) => setSourceAccount(event.target.value)}
                  required
                >
                  {activeAccounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name} · {money(account.balance)}
                    </option>
                  ))}
                </select>
              </label>
              {kind === "transfer" && !hasDestinations && (
                <p className="error">
                  Crea prima un salvadanaio per il versamento.
                </p>
              )}
              <button
                type="submit"
                disabled={busy || (kind === "transfer" && !hasDestinations)}
              >
                {busy ? "Creazione…" : "Crea automazione"}
              </button>
            </form>
          )}
        </section>

        <section className="card">
          <h2>Le tue automazioni ({automations.length})</h2>
          {automations.length === 0 ? (
            <p className="muted">Nessuna automazione impostata.</p>
          ) : (
            <ul className="entity-list">
              {automations.map((automation) => {
                const pending = pendingByRule.filter(
                  (execution) => execution.automation_ref === automation.id,
                );
                const chosen = selected[automation.id] ?? [];
                const ruleLabel =
                  automation.kind === "expense"
                    ? automation.description
                    : automation.savings_name;
                return (
                  <li className="automation-card" key={automation.id}>
                    <div className="entity-card-head">
                      <div>
                        <strong>
                          {money(automation.amount)} · {automation.interval_label}
                        </strong>
                        <span className="muted small">
                          {" "}
                          · {automation.source_account_name ?? "conto mancante"}
                          {automation.kind === "expense"
                            ? ` · ${automation.description}`
                            : ` → ${automation.savings_name}`}
                        </span>
                      </div>
                      <div className="entity-side">
                        <span className="badge">{automation.kind_label}</span>
                        <span
                          className={`badge ${
                            automation.status === "active"
                              ? "ok"
                              : automation.status === "suspended"
                                ? "rejected"
                                : "pending"
                          }`}
                        >
                          {automation.status_label}
                        </span>
                      </div>
                    </div>
                    <p className="muted small">
                      Prossima esecuzione: {prettyDate(automation.next_run_on)}
                      {pending.length > 0 && ` · ${pending.length} in attesa`}
                      {automation.advance_notice_days > 0
                        ? ` · avviso ${automation.advance_notice_days} giorni prima`
                        : " · avviso saldo disattivato"}
                    </p>
                    <div className="inline-form">
                      <button
                        type="button"
                        className="secondary"
                        disabled={busy}
                        onClick={() => void runOne(automation)}
                      >
                        Esegui ora
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        disabled={busy}
                        onClick={() => void toggleStatus(automation)}
                      >
                        {automation.status === "active" ? "Metti in pausa" : "Riattiva"}
                      </button>
                      <button
                        type="button"
                        className="danger"
                        disabled={busy}
                        onClick={() => {
                          void runAction(async () => {
                            await api.deleteAutomation(automation.id);
                            notify(
                              `Automazione eliminata (${ruleLabel ?? "regola"}).`,
                              {
                                label: "Annulla",
                                onClick: () => {
                                  api
                                    .restoreTrash("automation", automation.id)
                                    .then(() => load())
                                    .catch((err) =>
                                      setError(
                                        err instanceof Error
                                          ? err.message
                                          : "Ripristino non riuscito.",
                                      ),
                                    );
                                },
                              },
                            );
                          }, "Automazione eliminata.");
                        }}
                      >
                        Elimina
                      </button>
                    </div>

                    <details>
                      <summary className="muted small">
                        Modifica importo, descrizione, periodicità, avviso e
                        prossima esecuzione
                      </summary>
                      <AutomationEditForm
                        automation={automation}
                        busy={busy}
                        onSave={(data) => {
                          void runAction(async () => {
                            await api.updateAutomation(automation.id, data);
                          }, "Automazione aggiornata.");
                        }}
                      />
                    </details>

                    {pending.length > 0 && (
                      <div className="pending-box">
                        <strong>
                          Occorrenze perse da scegliere ({pending.length})
                        </strong>
                        <p className="muted small">
                          Le selezionate vengono recuperate con la data originale;
                          le altre vengono saltate.
                        </p>
                        <ul className="entity-list">
                          {pending.map((execution) => (
                            <li key={execution.id}>
                              <label className="checkbox-row">
                                <input
                                  type="checkbox"
                                  checked={chosen.includes(execution.id)}
                                  onChange={() =>
                                    toggleSelected(automation.id, execution.id)
                                  }
                                />
                                {prettyDate(execution.scheduled_date)} ·{" "}
                                {money(execution.amount)}
                              </label>
                            </li>
                          ))}
                        </ul>
                        <div className="inline-form">
                          <button
                            type="button"
                            disabled={busy || chosen.length === 0}
                            onClick={() => void resolve(automation, chosen)}
                          >
                            Recupera selezionate ({chosen.length})
                          </button>
                          <button
                            type="button"
                            className="secondary"
                            disabled={busy}
                            onClick={() => void resolve(automation, [])}
                          >
                            Salta tutte
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      <section className="card">
        <div className="card-heading">
          <h2>Esecuzioni recenti</h2>
          <span className="muted small">{executions.length} occorrenze</span>
        </div>
        {executions.length === 0 ? (
          <p className="muted">Nessuna occorrenza registrata.</p>
        ) : (
          <ul className="entity-list">
            {executions.map((execution) => (
              <li key={execution.id}>
                <div>
                  <strong>{execution.automation_name}</strong>
                  <span className="muted small">
                    {" "}
                    · {prettyDate(execution.scheduled_date)} ·{" "}
                    {money(execution.amount)}
                    {execution.corrected && " · corretta"}
                    {execution.transaction &&
                      ` · movimento #${execution.transaction}`}
                  </span>
                  {execution.failure_message && (
                    <div className="muted small">{execution.failure_message}</div>
                  )}
                </div>
                <span className={`badge ${executionBadge(execution.status)}`}>
                  {execution.status_label}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <div className="card-heading">
          <h2>Notifiche</h2>
          {unread > 0 && (
            <button
              type="button"
              className="secondary"
              disabled={busy}
              onClick={() =>
                void runAction(async () => {
                  const result = await api.markNotificationsRead();
                  setUnread(result.unread_count);
                }, "Notifiche segnate come lette.")
              }
            >
              Segna tutte come lette ({unread})
            </button>
          )}
        </div>
        {notifications.length === 0 ? (
          <p className="muted">Nessuna notifica.</p>
        ) : (
          <ul className="entity-list">
            {notifications.map((notification) => (
              <li
                key={notification.id}
                className={notification.is_read ? "archived" : undefined}
              >
                <div>
                  <span className="badge pending">{notification.kind_label}</span>
                  <div>{notification.message}</div>
                </div>
                <span className="muted small">
                  {new Date(notification.created_at).toLocaleDateString("it-IT")}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
