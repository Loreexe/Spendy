import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import { Download, FileSpreadsheet, PackageOpen, Upload } from "lucide-react";
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

function visible(query: string, keywords: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  return keywords.toLowerCase().includes(needle);
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

function PanelIcon({ children }: { children: React.ReactNode }) {
  return <span className="panel-icon">{children}</span>;
}

export function ImportExportSection({ query = "" }: { query?: string }) {
  const [exporting, setExporting] = useState(false);
  const [exportingCsv, setExportingCsv] = useState(false);
  const [exportingInvestments, setExportingInvestments] = useState(false);
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

  async function downloadCsv() {
    setError(null);
    setExportingCsv(true);
    try {
      await api.exportTransactions();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExportingCsv(false);
    }
  }

  async function downloadInvestments() {
    setError(null);
    setExportingInvestments(true);
    try {
      await api.exportInvestments();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExportingInvestments(false);
    }
  }

  async function chooseArchive(event: ChangeEvent<HTMLInputElement>) {    const selected = event.target.files?.[0] ?? null;
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

  if (
    !visible(
      query,
      "import export esporta ripristina archivio csv backup importa movimenti zip",
    )
  ) {
    return null;
  }

  return (
    <section className="profile-section">
      <div className="section-heading">
        <h2>Import ed export</h2>
      </div>

      <div className="settings-row">
        <article className="export-panel">
          <div className="export-panel-head">
            <PanelIcon>
              <Download size={18} aria-hidden="true" />
            </PanelIcon>
            <h3>Esporta archivio</h3>
          </div>
          <div className="actions">
            <button
              type="button"
              onClick={() => void downloadArchive()}
              disabled={exporting}
            >
              {exporting ? "Preparazione…" : "Scarica archivio CSV (ZIP)"}
            </button>
          </div>
        </article>

        <article className="export-panel">
          <div className="export-panel-head">
            <PanelIcon>
              <Upload size={18} aria-hidden="true" />
            </PanelIcon>
            <h3>Ripristina archivio</h3>
          </div>
          <label className="file-field">
            <Upload size={16} aria-hidden="true" />
            <span>{file ? file.name : "Scegli un archivio ZIP"}</span>
            <input
              ref={input}
              type="file"
              accept=".zip,application/zip"
              aria-label="Archivio ZIP da ripristinare"
              onChange={chooseArchive}
              disabled={analyzing || restoring}
            />
          </label>
          {analyzing && <p className="muted small">Analisi dell&apos;archivio…</p>}
        </article>
      </div>

      <article className="export-panel">
        <div className="export-panel-head">
          <PanelIcon>
            <FileSpreadsheet size={18} aria-hidden="true" />
          </PanelIcon>
          <h3>Importa ed esporta CSV</h3>
        </div>
        <div className="actions">
          <Link className="button secondary" to="/import">
            Importa movimenti CSV
          </Link>
          <button
            type="button"
            className="secondary"
            onClick={() => void downloadCsv()}
            disabled={exportingCsv}
          >
            {exportingCsv ? "Preparazione…" : "Esporta movimenti CSV"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => void downloadInvestments()}
            disabled={exportingInvestments}
          >
            {exportingInvestments ? "Preparazione…" : "Esporta investimenti CSV"}
          </button>
        </div>
      </article>

      {analysis && (
        <article className="export-panel export-preview">
          <div className="export-panel-head">
            <PanelIcon>
              <PackageOpen size={18} aria-hidden="true" />
            </PanelIcon>
            <h3>Anteprima archivio</h3>
          </div>
          <p className="muted small">
            <strong>{analysis.manifest.profilo || "Profilo"}</strong>
            {" · "}
            {dateLabel(analysis.manifest.generato_il)}
            {" · "}v{analysis.manifest.versione_app}
          </p>
          <div className="preview-grid">
            <div>
              <span>Conti</span>
              <strong>{analysis.summary.accounts}</strong>
            </div>
            <div>
              <span>Salvadanai</span>
              <strong>{analysis.summary.savings}</strong>
            </div>
            <div>
              <span>Movimenti</span>
              <strong>{analysis.summary.transactions}</strong>
            </div>
            <div>
              <span>Righe contabili</span>
              <strong>{analysis.summary.lines}</strong>
            </div>
            <div>
              <span>Posizioni</span>
              <strong>{analysis.summary.positions}</strong>
            </div>
            <div>
              <span>Operazioni</span>
              <strong>{analysis.summary.investment_operations}</strong>
            </div>
          </div>
          <dl className="facts">
            <div>
              <dt>Costo investimenti</dt>
              <dd>{money(analysis.summary.investments_cost)}</dd>
            </div>
            <div>
              <dt>Valore investimenti</dt>
              <dd>{money(analysis.summary.investments_value)}</dd>
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
                {analysis.summary.from ?? "—"} → {analysis.summary.to ?? "—"}
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
          <div className="actions">
            <button
              type="button"
              onClick={() => void confirmRestore()}
              disabled={!analysis.can_restore || restoring}
            >
              {restoring ? "Ripristino…" : "Ripristina archivio"}
            </button>
          </div>
        </article>
      )}

      {result && (
        <article className="export-panel export-preview">
          <div className="export-panel-head">
            <PanelIcon>
              <PackageOpen size={18} aria-hidden="true" />
            </PanelIcon>
            <h3>Ripristino completato</h3>
          </div>
          <p className="muted small">
            {result.accounts} conti, {result.savings} salvadanai,{" "}
            {result.transactions} movimenti, {result.positions} posizioni e{" "}
            {result.investment_operations} operazioni di investimento.
          </p>
          <dl className="facts">
            <div>
              <dt>Saldo conti</dt>
              <dd>{money(result.accounts_total)}</dd>
            </div>
            <div>
              <dt>Saldo salvadanai</dt>
              <dd>{money(result.savings_total)}</dd>
            </div>
            <div>
              <dt>Investimenti</dt>
              <dd>
                {money(result.investments_cost)} (valore{" "}
                {money(result.investments_value)})
              </dd>
            </div>
            <div>
              <dt>Patrimonio</dt>
              <dd>{money(result.patrimony_total)}</dd>
            </div>
          </dl>
          <div className="actions">
            <Link className="button secondary" to="/">
              Vai alla dashboard
            </Link>
          </div>
        </article>
      )}

      {error && <p className="error">{error}</p>}
    </section>
  );
}
