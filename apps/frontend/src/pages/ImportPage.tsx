import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
} from "react";
import { Link } from "react-router-dom";
import {
  api,
  ApiError,
  type ImportAnalysis,
  type ImportResult,
  type ImportRow,
  type ImportRowInput,
} from "../api";
import { money } from "../format";

type Step = "upload" | "review" | "summary" | "done";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return err instanceof Error ? err.message : "Operazione non riuscita.";
}

function toInput(row: ImportRow): ImportRowInput {
  return {
    date: row.date,
    description: row.description,
    category: row.category,
    account: row.account,
    amount: row.amount,
    not_duplicate: row.not_duplicate,
  };
}

function kindLabel(row: ImportRow): string {
  if (row.kind === "opening") return "Apertura";
  if (row.kind === "income") return "Entrata";
  if (row.kind === "expense") return "Uscita";
  return "—";
}

export function ImportPage() {
  const [step, setStep] = useState<Step>("upload");
  const [rows, setRows] = useState<ImportRowInput[]>([]);
  const [analysis, setAnalysis] = useState<ImportAnalysis | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [reading, setReading] = useState(false);
  const [stale, setStale] = useState(false);
  const pending = useRef(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const runAnalyze = useCallback(async (nextRows: ImportRowInput[]) => {
    if (!nextRows.length) {
      setAnalysis(null);
      setRows([]);
      setStep("upload");
      setStale(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const data = await api.analyzeImportRows(nextRows);
      setAnalysis(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      setStale(false);
    }
  }, []);

  useEffect(() => {
    if (!pending.current) return;
    const timer = window.setTimeout(() => {
      pending.current = false;
      void runAnalyze(rows);
    }, 450);
    return () => window.clearTimeout(timer);
  }, [rows, runAnalyze]);

  function updateRow(index: number, patch: Partial<ImportRowInput>) {
    setRows((current) =>
      current.map((row, position) =>
        position === index ? { ...row, ...patch } : row,
      ),
    );
    setStale(true);
    pending.current = true;
  }

  function discardRow(index: number) {
    const next = rows.filter((_, position) => position !== index);
    if (!next.length) {
      reset();
      return;
    }
    setRows(next);
    setAnalysis((current) =>
      current
        ? {
            ...current,
            rows: current.rows.filter((_, position) => position !== index),
            summary: { ...current.summary, can_confirm: false },
          }
        : current,
    );
    setStale(true);
    pending.current = true;
  }

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setReading(true);
    setError(null);
    try {
      const data = await api.analyzeImportFile(file);
      setAnalysis(data);
      setRows(data.rows.map(toInput));
      setStep("review");
      setStale(false);
      pending.current = false;
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setReading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function downloadTemplate() {
    setError(null);
    try {
      await api.downloadImportTemplate();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function confirmImport() {
    setBusy(true);
    setError(null);
    try {
      const data = await api.confirmImport(rows);
      setResult(data);
      setStep("done");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setStep("upload");
    setRows([]);
    setAnalysis(null);
    setResult(null);
    setError(null);
    setStale(false);
    pending.current = false;
  }

  const canAdvance = Boolean(
    analysis && analysis.summary.can_confirm && !stale && !busy,
  );

  return (
    <div className="stack-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Movimenti</p>
          <h1>Importa movimenti</h1>
        </div>
        {step !== "upload" && step !== "done" && (
          <button type="button" className="secondary" onClick={reset}>
            Annulla
          </button>
        )}
      </div>

      {error && <div className="error">{error}</div>}

      {step === "upload" && (
        <>
          <section className="card">
            <h2 className="card-heading">1. Scarica il modello</h2>
            <p className="muted">
              Il file di esempio contiene l&apos;intestazione e due righe
              marcate <code>ESEMPIO</code>: cancellale e inserisci i tuoi
              movimenti. Formato: <code>GG-MM-AAAA</code>, importo con la
              virgola, separatore <code>;</code>.
            </p>
            <button type="button" onClick={downloadTemplate}>
              Scarica modello CSV
            </button>
          </section>

          <section className="card">
            <h2 className="card-heading">2. Carica il file compilato</h2>
            <p className="muted">
              Il file viene analizzato prima di scrivere qualsiasi dato: puoi
              correggere gli errori, scartare righe e vedere il riepilogo prima
              della conferma.
            </p>
            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              onChange={handleFile}
              disabled={reading}
            />
            {reading && <p className="muted small">Analisi in corso…</p>}
          </section>

          <section className="card">
            <h2 className="card-heading">Regole dei saldi</h2>
            <p className="muted small">
              Il saldo di ogni conto non può mai andare sotto zero, in nessun
              punto della cronologia. La prima riga per data di un nuovo conto è
              la sua apertura e deve essere negativa (entrata).
            </p>
          </section>
        </>
      )}

      {step === "review" && analysis && (
        <>
          <section className="card">
            <div className="page-heading">
              <h2 className="card-heading">Anteprima</h2>
              <span className="muted small">
                {analysis.summary.rows_ok}/{analysis.summary.rows_total} righe
                valide · {analysis.summary.accounts_to_create} conti da creare
              </span>
            </div>

            {stale || busy ? (
              <p className="muted small">Verifica in corso…</p>
            ) : null}

            {analysis.file_errors.length > 0 && (
              <div className="error">
                <strong>Errori nel file</strong>
                <ul>
                  {analysis.file_errors.map((issue, position) => (
                    <li key={`${position}-${issue.code}`}>{issue.message}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="table-wrap">
              <table className="import-table">
                <thead>
                  <tr>
                    <th>Riga</th>
                    <th>Data</th>
                    <th>Descrizione</th>
                    <th>Categoria</th>
                    <th>Conto</th>
                    <th>Importo</th>
                    <th>Tipo</th>
                    <th>Esito</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {analysis.rows.map((row, index) => (
                    <tr
                      key={`${index}-${row.date}-${row.amount}`}
                      className={row.errors.length ? "row-error" : undefined}
                    >
                      <td className="muted small">{row.row_number}</td>
                      <td>
                        <input
                          value={rows[index]?.date ?? ""}
                          onChange={(event) =>
                            updateRow(index, { date: event.target.value })
                          }
                          aria-label={`Data riga ${row.row_number}`}
                        />
                      </td>
                      <td>
                        <input
                          value={rows[index]?.description ?? ""}
                          onChange={(event) =>
                            updateRow(index, { description: event.target.value })
                          }
                          aria-label={`Descrizione riga ${row.row_number}`}
                        />
                      </td>
                      <td>
                        <input
                          value={rows[index]?.category ?? ""}
                          readOnly
                          className="muted"
                          aria-label={`Categoria riga ${row.row_number}`}
                        />
                      </td>
                      <td>
                        <input
                          value={rows[index]?.account ?? ""}
                          onChange={(event) =>
                            updateRow(index, { account: event.target.value })
                          }
                          aria-label={`Conto riga ${row.row_number}`}
                        />
                      </td>
                      <td>
                        <input
                          value={rows[index]?.amount ?? ""}
                          onChange={(event) =>
                            updateRow(index, { amount: event.target.value })
                          }
                          aria-label={`Importo riga ${row.row_number}`}
                        />
                      </td>
                      <td className="small">{kindLabel(row)}</td>
                      <td className="small">
                        {row.errors.map((issue) => (
                          <span key={issue.code} className="error-text">
                            {issue.message}
                          </span>
                        ))}
                        {row.warnings.map((issue) => (
                          <span key={issue.code} className="muted">
                            {issue.message}
                          </span>
                        ))}
                        {row.errors.some(
                          (issue) =>
                            issue.code === "duplicate_in_file" ||
                            issue.code === "duplicate_in_database",
                        ) && (
                          <label className="checkbox-row">
                            <input
                              type="checkbox"
                              checked={rows[index]?.not_duplicate ?? false}
                              onChange={(event) =>
                                updateRow(index, {
                                  not_duplicate: event.target.checked,
                                })
                              }
                            />
                            Non è un duplicato
                          </label>
                        )}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="danger"
                          onClick={() => discardRow(index)}
                        >
                          Scarta
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="muted small">
              La colonna «Categoria» è ignorata: non esiste ancora un campo per
              le categorie.
            </p>
          </section>

          <div className="two-columns">
            <section className="card">
              <h2 className="card-heading">Conti</h2>
              <ul className="balance-list">
                {analysis.accounts.map((account) => (
                  <li key={account.normalized}>
                    <span>
                      <strong>{account.name}</strong>{" "}
                      <span className="muted small">
                        ({account.rows} righe)
                      </span>
                    </span>
                    <span className="small">
                      {account.state === "existing" && "esistente"}
                      {account.state === "new" && "verrà creato"}
                      {account.state === "similar" && (
                        <span className="error-text">
                          simile a «{account.similar_to}»: verrà creato un nuovo
                          conto
                        </span>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <section className="card">
              <h2 className="card-heading">Avvisi</h2>
              {analysis.overlaps.length === 0 ? (
                <p className="muted small">Nessuna sovrapposizione di periodo.</p>
              ) : (
                <ul className="balance-list">
                  {analysis.overlaps.map((overlap) => (
                    <li key={overlap.account}>
                      <span>{overlap.account}</span>
                      <span className="small muted">
                        {overlap.movements} movimenti già presenti
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <div className="actions">
            <button
              type="button"
              onClick={() => setStep("summary")}
              disabled={!canAdvance}
            >
              Avanti
            </button>
            {!canAdvance && (
              <span className="muted small">
                Correggi o scarta le righe con errori per proseguire.
              </span>
            )}
          </div>
        </>
      )}

      {step === "summary" && analysis && (
        <>
          <section className="card">
            <h2 className="card-heading">Riepilogo</h2>
            <div className="stat-grid">
              <div className="stat">
                <span className="stat-label">Righe</span>
                <strong>{analysis.summary.rows_ok}</strong>
              </div>
              <div className="stat">
                <span className="stat-label">Conti da creare</span>
                <strong>{analysis.summary.accounts_to_create}</strong>
              </div>
              <div className="stat">
                <span className="stat-label">Entrate</span>
                <strong>{money(analysis.summary.income_total)}</strong>
              </div>
              <div className="stat">
                <span className="stat-label">Uscite</span>
                <strong>{money(analysis.summary.expense_total)}</strong>
              </div>
              <div className="stat">
                <span className="stat-label">Aperture</span>
                <strong>{money(analysis.summary.openings_total)}</strong>
              </div>
              <div className="stat">
                <span className="stat-label">Netto importato</span>
                <strong>{money(analysis.summary.net_total)}</strong>
              </div>
            </div>

            <h3>Saldi dopo l&apos;import</h3>
            <ul className="balance-list">
              {analysis.summary.balances.map((balance) => (
                <li key={balance.name}>
                  <span>{balance.name}</span>
                  <strong>{money(balance.final_balance)}</strong>
                </li>
              ))}
            </ul>

            <div className="actions">
              <button type="button" onClick={confirmImport} disabled={busy}>
                {busy ? "Importazione…" : "Conferma e importa"}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => setStep("review")}
                disabled={busy}
              >
                Torna all&apos;anteprima
              </button>
            </div>
          </section>
        </>
      )}

      {step === "done" && result && (
        <section className="card">
          <h2 className="card-heading">Import completato</h2>
          <p className="notice">
            {result.created_transactions} movimenti inseriti
            {result.created_accounts.length === 1
              ? ", 1 conto creato"
              : result.created_accounts.length > 1
                ? `, ${result.created_accounts.length} conti creati`
                : ""}
            .
          </p>
          <div className="stat-grid">
            <div className="stat">
              <span className="stat-label">Entrate</span>
              <strong>{money(result.income_total)}</strong>
            </div>
            <div className="stat">
              <span className="stat-label">Uscite</span>
              <strong>{money(result.expense_total)}</strong>
            </div>
            <div className="stat">
              <span className="stat-label">Aperture</span>
              <strong>{money(result.openings_total)}</strong>
            </div>
            <div className="stat">
              <span className="stat-label">Netto importato</span>
              <strong>{money(result.net_total)}</strong>
            </div>
          </div>

          <h3>Saldi</h3>
          <ul className="balance-list">
            {result.accounts.map((account) => (
              <li key={account.name}>
                <span>{account.name}</span>
                <strong>{money(account.balance)}</strong>
              </li>
            ))}
          </ul>

          <div className="actions">
            <Link className="button" to="/movements">
              Vai ai movimenti
            </Link>
            <button type="button" className="secondary" onClick={reset}>
              Importa un altro file
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
