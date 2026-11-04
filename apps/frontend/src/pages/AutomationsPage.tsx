import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  type Account,
  type AutomationExecution,
  type AutomationExecutionStatus,
  type AutomationFrequency,
  type FinanceNotification,
  type SavingsAccount,
  type SavingsAutomation,
} from "../api";
import { LoadingScreen } from "../components/Guards";
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
  automation: SavingsAutomation;
  busy: boolean;
  onSave: (data: {
    amount: string;
    frequency: AutomationFrequency;
    next_run_on: string;
  }) => void;
}) {
  const [amount, setAmount] = useState(automation.amount);
  const [frequency, setFrequency] = useState(automation.frequency);
  const [nextRunOn, setNextRunOn] = useState(automation.next_run_on);

  return (
    <form
      className="inline-form"
      onSubmit={(event) => {
        event.preventDefault();
        onSave({ amount, frequency, next_run_on: nextRunOn });
      }}
    >
      <input
        type="number"
        step="0.01"
        min="0.01"
        value={amount}
        onChange={(event) => setAmount(event.target.value)}
        required
      />
      <select
        value={frequency}
        onChange={(event) =>
          setFrequency(event.target.value as AutomationFrequency)
        }
      >
        <option value="daily">Ogni giorno</option>
        <option value="weekly">Ogni settimana</option>
        <option value="monthly">Ogni mese</option>
        <option value="yearly">Ogni anno</option>
      </select>
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
  const [automations, setAutomations] = useState<SavingsAutomation[]>([]);
  const [executions, setExecutions] = useState<AutomationExecution[]>([]);
  const [notifications, setNotifications] = useState<FinanceNotification[]>([]);
  const [unread, setUnread] = useState(0);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [savings, setSavings] = useState<SavingsAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const [amount, setAmount] = useState("");
  const [frequency, setFrequency] = useState<AutomationFrequency>("monthly");
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
    if (!sourceAccount || !destination) {
      setError("Servono un conto di partenza e un salvadanaio di destinazione.");
      return;
    }
    await runAction(
      async () => {
        await api.createAutomation({
          savings: Number(destination),
          source_account: Number(sourceAccount),
          amount,
          frequency,
          next_run_on: nextRunOn,
        });
        setAmount("");
      },
      "Automazione creata.",
    );
  }

  async function toggleStatus(automation: SavingsAutomation) {
    const next = automation.status === "active" ? "paused" : "active";
    await runAction(
      async () => {
        await api.updateAutomation(automation.id, { status: next });
      },
      next === "paused" ? "Automazione messa in pausa." : "Automazione riattivata.",
    );
  }

  async function runOne(automation: SavingsAutomation) {
    await runAction(async () => {
      const result = await api.runAutomation(automation.id);
      return (
        `Esecuzione: ${result.outcome.executed} eseguite, ` +
        `${result.outcome.pending_choice} in attesa di scelta.`
      );
    }, "Automazione elaborata.");
  }

  async function resolve(
    automation: SavingsAutomation,
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
            Trasferimenti periodici dal conto al salvadanaio, con recupero delle
            occorrenze perse e storico delle esecuzioni.
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
                `${result.outcome.pending_choice} in attesa di scelta.`
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
          {activeAccounts.length === 0 || !hasDestinations ? (
            <p className="muted">
              Serve almeno un conto attivo e un salvadanaio: creali prima di
              impostare un'automazione.
            </p>
          ) : (
            <form onSubmit={handleCreate} className="stack">
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
                <select
                  value={frequency}
                  onChange={(event) =>
                    setFrequency(event.target.value as AutomationFrequency)
                  }
                >
                  <option value="weekly">Ogni settimana</option>
                  <option value="monthly">Ogni mese</option>
                  <option value="yearly">Ogni anno</option>
                  <option value="daily">Ogni giorno</option>
                </select>
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
                Conto di partenza
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
              <button type="submit" disabled={busy}>
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
                return (
                  <li className="automation-card" key={automation.id}>
                    <div className="entity-card-head">
                      <div>
                        <strong>
                          {money(automation.amount)} · {automation.frequency_label}
                        </strong>
                        <span className="muted small">
                          {" "}
                          · {automation.source_account_name ?? "conto mancante"} →{" "}
                          {automation.savings_name}
                        </span>
                      </div>
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
                    <p className="muted small">
                      Prossima esecuzione: {prettyDate(automation.next_run_on)}
                      {pending.length > 0 && ` · ${pending.length} in attesa`}
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
                          if (
                            !window.confirm(
                              `Eliminare l'automazione su "${automation.savings_name}"? ` +
                                "Lo storico delle esecuzioni resta disponibile.",
                            )
                          ) {
                            return;
                          }
                          void runAction(
                            () => api.deleteAutomation(automation.id),
                            "Automazione eliminata.",
                          );
                        }}
                      >
                        Elimina
                      </button>
                    </div>

                    <details>
                      <summary className="muted small">
                        Modifica importo, periodicità e prossima esecuzione
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
