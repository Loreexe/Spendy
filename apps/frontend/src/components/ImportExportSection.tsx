import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import {
  api,
  ApiError,
  type ArchiveAnalysis,
  type ArchiveRestoreResult,
} from "../api";
import { money } from "../format";

function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return err instanceof Error ? err.message : "Operazione non riuscita.";
}

function dateLabel(value: string | null): string {
  if (!value) return "nessuna data";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("it-IT", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function BalanceList({
  title,
  items,
}: {
  title: string;
  items: { name: string; balance: string }[];
}) {
  if (!items.length) return null;
  return (
    <div>
      <h4>{title}</h4>
      <dl className="facts">
        {items.map((item, index) => (
          <div key={`${item.name}-${index}`}>
            <dt>{item.name}</dt>
            <dd>{money(item.balance)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function ImportExportSection() {
  const [exporting, setExporting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<ArchiveAnalysis | null>(null);
  const [result, setResult] = useState<ArchiveRestoreResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);

  async function downloadArchive() {
    setError(null);
    setExporting(true);
    try {
      await api.exportArchive();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  async function chooseArchive(event: ChangeEvent<HTMLInputElement>) {
    const selected = event.target.files?.[0] ?? null;
    setFile(selected);
    setAnalysis(null);
    setResult(null);
    setError(null);
    if (!selected) return;
    setAnalyzing(true);
    try {
      setAnalysis(await api.analyzeArchive(selected));
    } catch (err) {
      setError(errorMessage(err));
      setFile(null);
      if (input.current) input.current.value = "";
    } finally {
      setAnalyzing(false);
    }
  }

  async function confirmRestore() {
    if (!file || !analysis?.can_restore) return;
    setRestoring(true);
    setError(null);
    try {
      const restored = await api.restoreArchive(file);
      setResult(restored);
      setAnalysis(null);
      setFile(null);
      if (input.current) input.current.value = "";
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRestoring(false);
    }
  }

  return (
    <section className="card">
      <h2>Import / Export</h2>
      <p className="muted">
        Il backup personale del profilo contiene conti, salvadanai e movimenti.
        È distinto dal backup globale del sistema e può essere usato per
        trasferire i dati su un altro server.
      </p>

      <div className="two-columns">
        <div className="stack">
          <h3>Importa</h3>
          <p className="muted small">
            I movimenti da un file CSV si importano con anteprima e controllo
            dei duplicati.
          </p>
          <div>
            <Link className="button secondary" to="/import">
              Importa movimenti CSV
            </Link>
          </div>

          <h3>Ripristina un archivio</h3>
          <p className="muted small">
            Carica lo ZIP creato con «Scarica archivio». Il ripristino è
            consentito solo su un profilo vuoto.
          </p>
          <input
            ref={input}
            type="file"
            accept=".zip,application/zip"
            aria-label="Archivio ZIP da ripristinare"
            onChange={chooseArchive}
            disabled={analyzing || restoring}
          />
          {analyzing && <p className="muted">Analisi dell&apos;archivio…</p>}
          {analysis && (
            <div className="notice">
              <p>
                <strong>{analysis.manifest.profilo || "Profilo"}</strong>
                {" · "}
                {dateLabel(analysis.manifest.generato_il)}
                {" · "}v{analysis.manifest.versione_app}
              </p>
              <dl className="facts">
                <div>
                  <dt>Conti</dt>
                  <dd>{analysis.summary.accounts}</dd>
                </div>
                <div>
                  <dt>Salvadanai</dt>
                  <dd>{analysis.summary.savings}</dd>
                </div>
                <div>
                  <dt>Movimenti</dt>
                  <dd>{analysis.summary.transactions}</dd>
                </div>
                <div>
                  <dt>Righe contabili</dt>
                  <dd>{analysis.summary.lines}</dd>
                </div>
                <div>
                  <dt>Saldo conti</dt>
                  <dd>{money(analysis.summary.accounts_total)}</dd>
                </div>
                <div>
                  <dt>Saldo salvadanai</dt>
                  <dd>{money(analysis.summary.savings_total)}</dd>
                </div>
                <div>
                  <dt>Patrimonio</dt>
                  <dd>{money(analysis.summary.patrimony_total)}</dd>
                </div>
                <div>
                  <dt>Periodo</dt>
                  <dd>
                    {analysis.summary.from ?? "—"} →{" "}
                    {analysis.summary.to ?? "—"}
                  </dd>
                </div>
              </dl>
              <BalanceList
                title="Saldi dei conti"
                items={analysis.summary.balances.accounts}
              />
              <BalanceList
                title="Saldi dei salvadanai"
                items={analysis.summary.balances.savings}
              />
              {analysis.warnings.map((warning) => (
                <p className="muted small" key={warning}>
                  {warning}
                </p>
              ))}
              {!analysis.can_restore && (
                <p className="error">{analysis.blocked_reason}</p>
              )}
              <button
                type="button"
                onClick={() => void confirmRestore()}
                disabled={!analysis.can_restore || restoring}
              >
                {restoring ? "Ripristino…" : "Ripristina archivio"}
              </button>
            </div>
          )}
          {result && (
            <div className="notice success">
              <p>
                Ripristino completato: {result.accounts} conti,{" "}
                {result.savings} salvadanai, {result.transactions} movimenti.
              </p>
              <p>
                Saldo conti {money(result.accounts_total)} · salvadanai{" "}
                {money(result.savings_total)} · patrimonio{" "}
                {money(result.patrimony_total)}
              </p>
              <Link className="button secondary" to="/">
                Vai alla dashboard
              </Link>
            </div>
          )}
        </div>

        <div className="stack">
          <h3>Esporta</h3>
          <p className="muted small">
            Scarica un archivio ZIP con quattro file CSV e un manifesto di
            controllo. Contiene tutti i dati del profilo, non solo i movimenti
            filtrati.
          </p>
          <div>
            <button
              type="button"
              onClick={() => void downloadArchive()}
              disabled={exporting}
            >
              {exporting ? "Preparazione…" : "Scarica archivio CSV (ZIP)"}
            </button>
          </div>
          <p className="muted small">
            Il registro filtrato si esporta dalla pagina Movimenti. Questo
            archivio non sostituisce il backup globale del database.
          </p>
        </div>
      </div>

      {error && <p className="error">{error}</p>}
    </section>
  );
}
