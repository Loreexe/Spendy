import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  api,
  type Account,
  type InvestmentCategory,
  type InvestmentOperation,
  type InvestmentOperationKind,
  type InvestmentOperationPayload,
  type InvestmentPortfolio,
  type InvestmentPosition,
  type InvestmentPositionDetail,
  type InvestmentPositionPayload,
  type InvestmentPositionUpdatePayload,
} from "../api";
import { LoadingScreen } from "../components/Guards";
import { ConfirmModal } from "../components/ConfirmModal";
import { useToast } from "../components/Toast";
import { money, signedMoney, todayISO } from "../format";

const CATEGORIES: { value: InvestmentCategory; label: string }[] = [
  { value: "stock", label: "Azione" },
  { value: "etf", label: "ETF" },
  { value: "bond", label: "Obbligazione" },
  { value: "fund", label: "Fondo" },
  { value: "crypto", label: "Crypto" },
  { value: "real_estate", label: "Immobile" },
  { value: "other", label: "Altro" },
];

const KINDS: { value: InvestmentOperationKind; label: string }[] = [
  { value: "opening", label: "Apertura" },
  { value: "buy", label: "Acquisto" },
  { value: "sell", label: "Vendita" },
  { value: "dividend", label: "Dividendo" },
];

function prettyDate(value: string | null): string {
  if (!value) return "—";
  return new Date(`${value}T12:00:00`).toLocaleDateString("it-IT");
}

function formatQuantity(value: string | null): string {
  if (value === null) return "—";
  return Number(value).toLocaleString("it-IT", { maximumFractionDigits: 8 });
}

function priceText(value: string | null): string {
  return value === null ? "—" : money(value);
}

function positionStatus(position: InvestmentPosition): {
  label: string;
  className: string;
} {
  if (position.archived) return { label: "Archiviata", className: "disabled" };
  if (Number(position.quantity) === 0) {
    return { label: "Chiusa", className: "pending" };
  }
  return { label: "Aperta", className: "ok" };
}

function NewPositionForm({
  busy,
  onCreate,
  onCancel,
}: {
  busy: boolean;
  onCreate: (payload: InvestmentPositionPayload) => Promise<boolean>;
  onCancel: () => void;
}) {
  const [name, setName] = useState("");
  const [category, setCategory] = useState<InvestmentCategory | "">("");
  const [identifier, setIdentifier] = useState("");
  const [currentPrice, setCurrentPrice] = useState("");
  const [hasOpening, setHasOpening] = useState(false);
  const [openingDate, setOpeningDate] = useState(todayISO());
  const [openingQuantity, setOpeningQuantity] = useState("");
  const [openingCost, setOpeningCost] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const payload: InvestmentPositionPayload = { name: name.trim() };
    if (category) payload.category = category;
    if (identifier.trim()) payload.identifier = identifier.trim();
    if (currentPrice.trim()) payload.current_price = currentPrice;
    if (hasOpening) {
      payload.opening = {
        date: openingDate,
        quantity: openingQuantity,
        total_cost: openingCost,
      };
    }
    const created = await onCreate(payload);
    if (created) {
      setName("");
      setCategory("");
      setIdentifier("");
      setCurrentPrice("");
      setHasOpening(false);
      setOpeningQuantity("");
      setOpeningCost("");
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Nome
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="ETF Mondo, Azioni Enel…"
            required
          />
        </label>
        <label>
          Categoria
          <select
            value={category}
            onChange={(event) =>
              setCategory(event.target.value as InvestmentCategory | "")
            }
          >
            <option value="">Nessuna categoria</option>
            {CATEGORIES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Identificativo (ticker/ISIN)
          <input
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            placeholder="IE00B4L5Y983"
          />
        </label>
        <label>
          Prezzo corrente (opzionale)
          <input
            type="number"
            step="any"
            min="0"
            value={currentPrice}
            onChange={(event) => setCurrentPrice(event.target.value)}
            placeholder="105.20"
          />
        </label>
      </div>

      <label className="checkbox-row">
        <input
          type="checkbox"
          checked={hasOpening}
          onChange={(event) => setHasOpening(event.target.checked)}
        />
        Possiedi già questa posizione
      </label>
      {hasOpening && (
        <>
          <p className="muted small">
            L&apos;apertura registra una posizione già posseduta: il conto
            investimenti non viene movimentato e il patrimonio aumenta del costo
            storico.
          </p>
          <div className="form-grid">
            <label>
              Data di apertura
              <input
                type="date"
                value={openingDate}
                onChange={(event) => setOpeningDate(event.target.value)}
                required
              />
            </label>
            <label>
              Quantità
              <input
                type="number"
                step="any"
                min="0"
                value={openingQuantity}
                onChange={(event) => setOpeningQuantity(event.target.value)}
                required
              />
            </label>
            <label>
              Costo totale
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={openingCost}
                onChange={(event) => setOpeningCost(event.target.value)}
                required
              />
            </label>
          </div>
        </>
      )}

      <div className="actions">
        <button type="submit" disabled={busy}>
          {busy ? "Creazione…" : "Crea posizione"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={onCancel}
          disabled={busy}
        >
          Annulla
        </button>
      </div>
    </form>
  );
}

function OperationForm({
  kind,
  editing,
  busy,
  onSubmit,
  onCancel,
}: {
  kind: InvestmentOperationKind;
  editing: InvestmentOperation | null;
  busy: boolean;
  onSubmit: (payload: InvestmentOperationPayload) => Promise<boolean>;
  onCancel: () => void;
}) {
  const [date, setDate] = useState(editing?.date ?? todayISO());
  const [quantity, setQuantity] = useState(editing?.quantity ?? "");
  const [priceMode, setPriceMode] = useState<"unit" | "total">("total");
  const [unitPrice, setUnitPrice] = useState(
    editing?.kind === "opening" ? "" : (editing?.unit_price ?? ""),
  );
  const [totalAmount, setTotalAmount] = useState(
    editing?.kind === "dividend" ? "" : (editing?.gross_amount ?? ""),
  );
  const [commission, setCommission] = useState(
    editing?.kind === "opening" || editing?.kind === "dividend"
      ? "0"
      : (editing?.commission ?? "0"),
  );
  const [amount, setAmount] = useState(
    editing?.kind === "dividend" ? editing.cash_amount : "",
  );
  const [description, setDescription] = useState(editing?.description ?? "");

  const gross =
    priceMode === "unit"
      ? Number(quantity || 0) * Number(unitPrice || 0)
      : Number(totalAmount || 0);
  const fee = kind === "buy" || kind === "sell" ? Number(commission || 0) : 0;
  const previewTotal =
    kind === "buy" ? gross + fee : kind === "sell" ? gross - fee : gross;

  async function submit(event: FormEvent) {
    event.preventDefault();
    const payload: InvestmentOperationPayload = {
      kind,
      date,
      description: description.trim(),
    };
    if (kind === "dividend") {
      payload.amount = amount;
    } else if (kind === "opening") {
      payload.quantity = quantity;
      payload.total_amount = totalAmount;
    } else {
      payload.quantity = quantity;
      payload.commission = commission || "0";
      if (priceMode === "unit") payload.unit_price = unitPrice;
      else payload.total_amount = totalAmount;
    }
    await onSubmit(payload);
  }

  return (
    <form className="stack" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Data
          <input
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
            required
          />
        </label>
        {kind === "dividend" ? (
          <label>
            Importo
            <input
              type="number"
              step="0.01"
              min="0.01"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              required
            />
          </label>
        ) : (
          <label>
            Quantità
            <input
              type="number"
              step="any"
              min="0"
              value={quantity}
              onChange={(event) => setQuantity(event.target.value)}
              required
            />
          </label>
        )}
      </div>

      {kind !== "dividend" && (
        <>
          {kind === "opening" ? (
            <label>
              Costo totale
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={totalAmount}
                onChange={(event) => setTotalAmount(event.target.value)}
                required
              />
            </label>
          ) : (
            <div className="form-grid">
              <label>
                Inserisci
                <select
                  value={priceMode}
                  onChange={(event) =>
                    setPriceMode(event.target.value as "unit" | "total")
                  }
                >
                  <option value="unit">Prezzo unitario</option>
                  <option value="total">Controvalore totale</option>
                </select>
              </label>
              {priceMode === "unit" ? (
                <label>
                  Prezzo unitario
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={unitPrice}
                    onChange={(event) => setUnitPrice(event.target.value)}
                    required
                  />
                </label>
              ) : (
                <label>
                  Controvalore totale
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={totalAmount}
                    onChange={(event) => setTotalAmount(event.target.value)}
                    required
                  />
                </label>
              )}
              <label>
                Commissione
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={commission}
                  onChange={(event) => setCommission(event.target.value)}
                />
              </label>
            </div>
          )}
          <p className="operation-preview">
            Totale: <strong>{money(previewTotal)}</strong>
            {kind === "buy" && (
              <span className="muted small"> · esce dal conto</span>
            )}
            {kind === "sell" && (
              <span className="muted small"> · entra nel conto</span>
            )}
          </p>
        </>
      )}

      <label>
        Descrizione (opzionale)
        <input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="PAC febbraio, dividendo trimestrale…"
        />
      </label>

      <div className="actions">
        <button type="submit" disabled={busy}>
          {busy ? "Salvataggio…" : editing ? "Salva operazione" : "Registra"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={onCancel}
          disabled={busy}
        >
          Annulla
        </button>
      </div>
    </form>
  );
}

function PositionDetail({
  position,
  onChanged,
  onDeleted,
}: {
  position: InvestmentPosition;
  onChanged: () => Promise<void>;
  onDeleted: () => Promise<void>;
}) {
  const [detail, setDetail] = useState<InvestmentPositionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editingPosition, setEditingPosition] = useState(false);
  const [operationForm, setOperationForm] = useState<{
    kind: InvestmentOperationKind;
    editing: InvestmentOperation | null;
  } | null>(null);
  const [name, setName] = useState(position.name);
  const [confirmDeletePosition, setConfirmDeletePosition] = useState(false);
  const [confirmDeleteOperation, setConfirmDeleteOperation] =
    useState<InvestmentOperation | null>(null);
  const { notify } = useToast();
  const [category, setCategory] = useState<InvestmentCategory | "">(
    position.category,
  );
  const [identifier, setIdentifier] = useState(position.identifier);
  const [currentPrice, setCurrentPrice] = useState(position.current_price ?? "");

  const loadDetail = useCallback(async () => {
    const data = await api.investmentPosition(position.id);
    setDetail(data);
  }, [position.id]);

  useEffect(() => {
    let active = true;
    setLoadingDetail(true);
    setDetail(null);
    setOperationForm(null);
    setEditingPosition(false);
    api
      .investmentPosition(position.id)
      .then((data) => {
        if (active) setDetail(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Caricamento non riuscito.",
          );
        }
      })
      .finally(() => {
        if (active) setLoadingDetail(false);
      });
    return () => {
      active = false;
    };
  }, [position.id]);

  const operations = detail?.operations ?? [];
  const open = Number(position.quantity) > 0;
  const archived = position.archived;

  function startEditing() {
    setName(position.name);
    setCategory(position.category);
    setIdentifier(position.identifier);
    setCurrentPrice(position.current_price ?? "");
    setEditingPosition(true);
  }

  async function savePosition(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const data: InvestmentPositionUpdatePayload = {
        name: name.trim(),
        category,
        identifier: identifier.trim(),
        current_price: currentPrice.trim() ? currentPrice : null,
      };
      await api.updateInvestmentPosition(position.id, data);
      setEditingPosition(false);
      setMessage("Posizione aggiornata.");
      await loadDetail();
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Salvataggio non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function toggleArchive() {
    const action = archived ? "riattivare" : "archiviare";
    if (
      !window.confirm(
        `Vuoi ${action} la posizione "${position.name}"? ` +
          (archived
            ? "Tornerà disponibile per nuove operazioni."
            : "Potrai registrare nuove operazioni solo dopo averla riattivata."),
      )
    ) {
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.updateInvestmentPosition(position.id, { archived: !archived });
      setMessage(archived ? "Posizione riattivata." : "Posizione archiviata.");
      await loadDetail();
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function removePosition() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.deleteInvestmentPosition(position.id);
      notify(`Posizione «${position.name}» eliminata.`, {
        label: "Annulla",
        onClick: () => {
          api
            .restoreTrash("position", position.id)
            .then(() => onChanged())
            .catch((err) =>
              setError(
                err instanceof Error ? err.message : "Ripristino non riuscito.",
              ),
            );
        },
      });
      setConfirmDeletePosition(false);
      await onDeleted();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eliminazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  async function submitOperation(
    payload: InvestmentOperationPayload,
  ): Promise<boolean> {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      if (operationForm?.editing) {
        const {
          date,
          quantity,
          unit_price,
          total_amount,
          commission,
          amount,
          description,
        } = payload;
        await api.updateInvestmentOperation(operationForm.editing.id, {
          date,
          quantity,
          unit_price,
          total_amount,
          commission,
          amount,
          description,
        });
        setMessage("Operazione aggiornata; i totali sono stati ricalcolati.");
      } else {
        await api.createInvestmentOperation(position.id, payload);
        setMessage("Operazione registrata.");
      }
      setOperationForm(null);
      await loadDetail();
      await onChanged();
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operazione non riuscita.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function removeOperation(operation: InvestmentOperation) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.deleteInvestmentOperation(operation.id);
      notify("Operazione eliminata; i totali sono stati ricalcolati.", {
        label: "Annulla",
        onClick: () => {
          api
            .restoreTrash("operation", operation.id)
            .then(() => {
              loadDetail();
              onChanged();
            })
            .catch((err) =>
              setError(
                err instanceof Error ? err.message : "Ripristino non riuscito.",
              ),
            );
        },
      });
      setConfirmDeleteOperation(null);
      setMessage("Operazione eliminata; i totali sono stati ricalcolati.");
      await loadDetail();
      await onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Eliminazione non riuscita.");
    } finally {
      setBusy(false);
    }
  }

  const status = positionStatus(position);

  return (
    <section className="card" id="position-detail">
      <div className="card-heading">
        <div>
          <h2>{position.name}</h2>
          <p className="muted small">
            {position.category_label || "Senza categoria"}
            {position.identifier ? ` · ${position.identifier}` : ""} ·{" "}
            <span className={`badge ${status.className}`}>{status.label}</span>
          </p>
        </div>
        <div className="actions">
          <button
            type="button"
            className="secondary"
            onClick={() => (editingPosition ? setEditingPosition(false) : startEditing())}
            disabled={busy}
          >
            {editingPosition ? "Chiudi modifica" : "Modifica posizione"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => void toggleArchive()}
            disabled={busy || (open && !archived)}
            title={
              open && !archived
                ? "Puoi archiviare solo quando la quantità è zero."
                : undefined
            }
          >
            {archived ? "Riattiva" : "Archivia"}
          </button>
          <button
            type="button"
            className="danger"
            onClick={() => setConfirmDeletePosition(true)}
            disabled={busy || loadingDetail || operations.length > 0}
            title={
              operations.length > 0
                ? "Elimina prima le operazioni della posizione."
                : undefined
            }
          >
            Elimina posizione
          </button>
        </div>
      </div>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="error">{error}</p>}
      {archived && (
        <p className="notice warning">
          Posizione archiviata: non accetta nuove operazioni finché non la
          riattivi.
        </p>
      )}

      <dl className="detail-facts">
        <div>
          <dt>Quantità</dt>
          <dd>{formatQuantity(position.quantity)}</dd>
        </div>
        <div>
          <dt>Costo medio</dt>
          <dd>{money(position.average_cost)}</dd>
        </div>
        <div>
          <dt>Costo residuo</dt>
          <dd>{money(position.cost)}</dd>
        </div>
        <div>
          <dt>Prezzo corrente</dt>
          <dd>
            {priceText(position.current_price)}
            {position.price_updated_on
              ? ` · ${prettyDate(position.price_updated_on)}`
              : ""}
          </dd>
        </div>
        <div>
          <dt>Valore corrente</dt>
          <dd>{priceText(position.current_value)}</dd>
        </div>
        <div>
          <dt>Plusvalenza non realizzata</dt>
          <dd>
            {position.unrealized_gain === null
              ? "—"
              : signedMoney(position.unrealized_gain)}
          </dd>
        </div>
        <div>
          <dt>Plusvalenze realizzate</dt>
          <dd>{signedMoney(position.realized_gain)}</dd>
        </div>
        <div>
          <dt>Dividendi</dt>
          <dd>{money(position.dividends)}</dd>
        </div>
      </dl>

      {editingPosition && (
        <form className="stack" onSubmit={savePosition}>
          <div className="form-grid">
            <label>
              Nome
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </label>
            <label>
              Categoria
              <select
                value={category}
                onChange={(event) =>
                  setCategory(event.target.value as InvestmentCategory | "")
                }
              >
                <option value="">Nessuna categoria</option>
                {CATEGORIES.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Identificativo (ticker/ISIN)
              <input
                value={identifier}
                onChange={(event) => setIdentifier(event.target.value)}
              />
            </label>
            <label>
              Prezzo corrente
              <input
                type="number"
                step="any"
                min="0"
                value={currentPrice}
                onChange={(event) => setCurrentPrice(event.target.value)}
                placeholder="Lascia vuoto se non disponibile"
              />
            </label>
          </div>
          <p className="muted small">
            Aggiornando il prezzo, la data del prezzo diventa oggi.
          </p>
          <div className="actions">
            <button type="submit" disabled={busy}>
              {busy ? "Salvataggio…" : "Salva posizione"}
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => setEditingPosition(false)}
              disabled={busy}
            >
              Annulla
            </button>
          </div>
        </form>
      )}

      <div className="detail-actions">
        {(["buy", "sell", "dividend"] as InvestmentOperationKind[]).map(
          (kind) => (
            <button
              key={kind}
              type="button"
              className="secondary"
              onClick={() => setOperationForm({ kind, editing: null })}
              disabled={busy || archived}
            >
              {KINDS.find((option) => option.value === kind)?.label}
            </button>
          ),
        )}
        {!loadingDetail && operations.length === 0 && (
          <button
            type="button"
            className="secondary"
            onClick={() => setOperationForm({ kind: "opening", editing: null })}
            disabled={busy || archived}
          >
            Apertura
          </button>
        )}
      </div>

      {operationForm && (
        <div className="pending-box">
          <div className="card-heading">
            <h3>
              {operationForm.editing ? "Modifica" : "Nuova"}{" "}
              {KINDS.find((option) => option.value === operationForm.kind)?.label}
            </h3>
            <span className="muted small">
              Il tipo di operazione non è modificabile: per cambiarlo elimina e
              ricrea l&apos;operazione.
            </span>
          </div>
          <OperationForm
            key={`${operationForm.kind}-${operationForm.editing?.id ?? "new"}`}
            kind={operationForm.kind}
            editing={operationForm.editing}
            busy={busy}
            onSubmit={submitOperation}
            onCancel={() => setOperationForm(null)}
          />
        </div>
      )}

      <div className="table-wrap">
        <table className="position-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Tipo</th>
              <th>Quantità</th>
              <th>Prezzo</th>
              <th>Commissione</th>
              <th>Cassa</th>
              <th>Costo rimosso</th>
              <th>Plusvalenza</th>
              <th>Descrizione</th>
              <th>Azioni</th>
            </tr>
          </thead>
          <tbody>
            {operations.length === 0 && (
              <tr>
                <td colSpan={10} className="muted">
                  {loadingDetail
                    ? "Caricamento operazioni…"
                    : "Nessuna operazione registrata."}
                </td>
              </tr>
            )}
            {operations.map((operation) => (
              <tr key={operation.id}>
                <td>{prettyDate(operation.date)}</td>
                <td>{operation.kind_label}</td>
                <td>{formatQuantity(operation.quantity)}</td>
                <td>
                  {operation.unit_price === null
                    ? "—"
                    : money(operation.unit_price)}
                </td>
                <td>
                  {operation.kind === "dividend" || operation.kind === "opening"
                    ? "—"
                    : money(operation.commission)}
                </td>
                <td>
                  {operation.kind === "opening"
                    ? "—"
                    : signedMoney(
                        operation.kind === "buy"
                          ? -Number(operation.cash_amount)
                          : operation.cash_amount,
                      )}
                </td>
                <td>
                  {operation.kind === "sell"
                    ? money(operation.cost_removed)
                    : "—"}
                </td>
                <td>
                  {operation.kind === "sell"
                    ? signedMoney(operation.realized_gain)
                    : "—"}
                </td>
                <td>{operation.description}</td>
                <td>
                  <div className="actions">
                    <button
                      type="button"
                      className="secondary"
                      onClick={() =>
                        setOperationForm({
                          kind: operation.kind,
                          editing: operation,
                        })
                      }
                      disabled={busy || archived}
                    >
                      Modifica
                    </button>
                    <button
                      type="button"
                      className="danger"
                      onClick={() => setConfirmDeleteOperation(operation)}
                      disabled={busy}
                    >
                      Elimina
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {confirmDeletePosition && (
        <ConfirmModal
          title={`Eliminare la posizione «${position.name}»?`}
          summary={[
            "Possibile solo se non ha operazioni.",
            "La posizione finisce nel cestino per 30 giorni.",
          ]}
          busy={busy}
          onConfirm={() => void removePosition()}
          onCancel={() => setConfirmDeletePosition(false)}
        />
      )}
      {confirmDeleteOperation && (
        <ConfirmModal
          title="Eliminare questa operazione?"
          summary={[
            `${confirmDeleteOperation.kind_label} del ${prettyDate(confirmDeleteOperation.date)}.`,
            "Il movimento di conto collegato sarà rimosso e quantità, costo e plusvalenze saranno ricalcolati.",
            "L'operazione finisce nel cestino per 30 giorni.",
          ]}
          busy={busy}
          onConfirm={() => void removeOperation(confirmDeleteOperation)}
          onCancel={() => setConfirmDeleteOperation(null)}
        />
      )}
    </section>
  );
}

export function InvestmentsPage() {
  const [portfolio, setPortfolio] = useState<InvestmentPortfolio | null>(null);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [accountChoice, setAccountChoice] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [portfolioData, accountsData] = await Promise.all([
      api.investments(),
      api.accounts(),
    ]);
    setPortfolio(portfolioData);
    setAccounts(accountsData.accounts);
  }, []);

  useEffect(() => {
    let active = true;
    setLoading(true);
    refresh()
      .catch((err) => {
        if (active) {
          setError(
            err instanceof Error ? err.message : "Caricamento non riuscito.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [refresh]);

  useEffect(() => {
    setAccountChoice(
      portfolio?.investment_account
        ? String(portfolio.investment_account.id)
        : "",
    );
  }, [portfolio?.investment_account?.id]);

  useEffect(() => {
    if (
      portfolio &&
      selectedId !== null &&
      !portfolio.positions.some((position) => position.id === selectedId)
    ) {
      setSelectedId(null);
    }
  }, [portfolio, selectedId]);

  async function reload() {
    try {
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Aggiornamento non riuscito.");
    }
  }

  async function saveAccount(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.setInvestmentAccount(
        accountChoice ? Number(accountChoice) : null,
      );
      setMessage("Conto investimenti aggiornato.");
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Salvataggio non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  async function createPosition(
    payload: InvestmentPositionPayload,
  ): Promise<boolean> {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const position = await api.createInvestmentPosition(payload);
      setShowNew(false);
      setMessage(`Posizione "${position.name}" creata.`);
      await reload();
      setSelectedId(position.id);
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Creazione non riuscita.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function exportCsv() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.exportInvestments();
      setMessage("Export investimenti scaricato.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export non riuscito.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <LoadingScreen />;

  const summary = portfolio?.summary ?? null;
  const investmentAccount = portfolio?.investment_account ?? null;
  const activeAccounts = accounts.filter(
    (account) =>
      !account.archived ||
      (investmentAccount !== null && account.id === investmentAccount.id),
  );
  const visiblePositions = (portfolio?.positions ?? []).filter(
    (position) => showArchived || !position.archived,
  );
  const selectedPosition =
    portfolio?.positions.find((position) => position.id === selectedId) ?? null;

  return (
    <div className="stack-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">Patrimonio</p>
          <h1>Investimenti</h1>
        </div>
        <div className="actions">
          <button
            type="button"
            className="secondary"
            onClick={() => void exportCsv()}
            disabled={busy}
          >
            Esporta CSV investimenti (ZIP)
          </button>
          <button
            type="button"
            onClick={() => setShowNew((value) => !value)}
            disabled={busy}
          >
            {showNew ? "Chiudi" : "Nuova posizione"}
          </button>
        </div>
      </section>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="error">{error}</p>}

      <section className="card">
        <div className="card-heading">
          <h2>Conto investimenti</h2>
          {investmentAccount && (
            <span className="badge ok">{investmentAccount.name}</span>
          )}
        </div>
        <form className="investment-account" onSubmit={saveAccount}>
          <label>
            Conto usato per acquisti, vendite e dividendi
            <select
              value={accountChoice}
              onChange={(event) => setAccountChoice(event.target.value)}
            >
              <option value="">Nessun conto</option>
              {activeAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy}>
            Salva
          </button>
        </form>
        {!investmentAccount && (
          <p className="notice warning">
            Scegli un conto per registrare acquisti, vendite e dividendi. Senza
            conto queste operazioni sono bloccate, ma puoi comunque aprire
            posizioni già possedute.
          </p>
        )}
        <p className="muted small">
          Il conto è personale e può essere cambiato: le operazioni già
          registrate restano sul conto usato allora.
        </p>
      </section>

      {showNew && (
        <section className="card">
          <h2>Nuova posizione</h2>
          <NewPositionForm
            busy={busy}
            onCreate={createPosition}
            onCancel={() => setShowNew(false)}
          />
        </section>
      )}

      {summary && (
        <section className="stat-grid">
          <div className="stat card">
            <span className="stat-label">Costo investito</span>
            <strong>{money(summary.total_cost)}</strong>
          </div>
          <div className="stat card">
            <span className="stat-label">Valore corrente</span>
            <strong>{money(summary.total_value)}</strong>
            <span className="muted small">solo posizioni con prezzo</span>
          </div>
          <div className="stat card">
            <span className="stat-label">Plusvalenza non realizzata</span>
            <strong className={Number(summary.total_unrealized) < 0 ? "negative" : "positive"}>
              {signedMoney(summary.total_unrealized)}
            </strong>
          </div>
          <div className="stat card">
            <span className="stat-label">Plusvalenze realizzate</span>
            <strong className={Number(summary.realized_gain) < 0 ? "negative" : "positive"}>
              {signedMoney(summary.realized_gain)}
            </strong>
          </div>
          <div className="stat card">
            <span className="stat-label">Dividendi incassati</span>
            <strong>{money(summary.dividends)}</strong>
          </div>
          <div className="stat card">
            <span className="stat-label">Posizioni senza prezzo</span>
            <strong>{summary.positions_without_price}</strong>
          </div>
        </section>
      )}

      <section className="card">
        <div className="card-heading">
          <h2>Posizioni ({visiblePositions.length})</h2>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(event) => setShowArchived(event.target.checked)}
            />
            Mostra archiviate
          </label>
        </div>
        {visiblePositions.length === 0 ? (
          <p className="muted">
            {portfolio?.positions.length
              ? "Nessuna posizione da mostrare con questo filtro."
              : "Nessuna posizione: crea la prima con “Nuova posizione”."}
          </p>
        ) : (
          <div className="table-wrap">
            <table className="position-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Categoria</th>
                  <th>Quantità</th>
                  <th>Costo medio</th>
                  <th>Costo residuo</th>
                  <th>Prezzo corrente</th>
                  <th>Valore corrente</th>
                  <th>Plusvalenza</th>
                  <th>Stato</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {visiblePositions.map((position) => {
                  const status = positionStatus(position);
                  return (
                    <tr
                      key={position.id}
                      className={position.id === selectedId ? "selected" : ""}
                    >
                      <td>
                        <strong>{position.name}</strong>
                        {position.identifier && (
                          <span className="muted small">
                            {" "}
                            · {position.identifier}
                          </span>
                        )}
                      </td>
                      <td>{position.category_label || "—"}</td>
                      <td>{formatQuantity(position.quantity)}</td>
                      <td>{money(position.average_cost)}</td>
                      <td>{money(position.cost)}</td>
                      <td>
                        {priceText(position.current_price)}
                        {position.price_updated_on && (
                          <span className="muted small">
                            {" "}
                            · {prettyDate(position.price_updated_on)}
                          </span>
                        )}
                      </td>
                      <td>{priceText(position.current_value)}</td>
                      <td
                        className={
                          position.unrealized_gain === null
                            ? ""
                            : Number(position.unrealized_gain) < 0
                              ? "negative"
                              : "positive"
                        }
                      >
                        {position.unrealized_gain === null
                          ? "—"
                          : signedMoney(position.unrealized_gain)}
                      </td>
                      <td>
                        <span className={`badge ${status.className}`}>
                          {status.label}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="secondary"
                          onClick={() => setSelectedId(position.id)}
                        >
                          Apri
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selectedPosition && (
        <PositionDetail
          key={selectedPosition.id}
          position={selectedPosition}
          onChanged={reload}
          onDeleted={async () => {
            setSelectedId(null);
            await reload();
          }}
        />
      )}
    </div>
  );
}
