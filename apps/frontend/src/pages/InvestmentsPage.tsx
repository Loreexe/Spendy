import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Archive, X } from "lucide-react";
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
  type SavingsAccount,
} from "../api";
import { LoadingScreen } from "../components/Guards";
import { ConfirmModal } from "../components/ConfirmModal";
import { EmptyState } from "../components/EmptyState";
import { SkeletonLines } from "../components/SkeletonLines";
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
  const [openingPrice, setOpeningPrice] = useState("");
  const [openingCost, setOpeningCost] = useState("");
  const [openingError, setOpeningError] = useState<string | null>(null);

  const qtyNum =
    openingQuantity.trim() === "" ? null : Number(openingQuantity);
  const priceNum = openingPrice.trim() === "" ? null : Number(openingPrice);
  const costNum = openingCost.trim() === "" ? null : Number(openingCost);
  const openingCount = [qtyNum, priceNum, costNum].filter(
    (value) => value !== null,
  ).length;
  let openingHint: { label: string; value: string } | null = null;
  if (openingCount === 2) {
    if (qtyNum !== null && priceNum !== null) {
      openingHint = {
        label: "Totale",
        value: money(String(qtyNum * priceNum)),
      };
    } else if (qtyNum !== null && costNum !== null) {
      openingHint = {
        label: "Prezzo",
        value: qtyNum > 0 ? formatQuantity(String(costNum / qtyNum)) : "—",
      };
    } else if (priceNum !== null && costNum !== null) {
      openingHint = {
        label: "Quantità",
        value: priceNum > 0 ? formatQuantity(String(costNum / priceNum)) : "—",
      };
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const payload: InvestmentPositionPayload = { name: name.trim() };
    if (category) payload.category = category;
    if (identifier.trim()) payload.identifier = identifier.trim();
    if (currentPrice.trim()) payload.current_price = currentPrice;
    if (hasOpening) {
      if (openingCount !== 2) {
        setOpeningError(
          "Inserisci due valori tra quantità, prezzo unitario e costo totale.",
        );
        return;
      }
      payload.opening = { date: openingDate };
      if (qtyNum !== null) payload.opening.quantity = openingQuantity;
      if (priceNum !== null) payload.opening.unit_price = openingPrice;
      if (costNum !== null) payload.opening.total_cost = openingCost;
    }
    const created = await onCreate(payload);
    if (created) {
      setName("");
      setCategory("");
      setIdentifier("");
      setCurrentPrice("");
      setHasOpening(false);
      setOpeningQuantity("");
      setOpeningPrice("");
      setOpeningCost("");
      setOpeningError(null);
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
              />
            </label>
            <label>
              Prezzo unitario
              <input
                type="number"
                step="any"
                min="0"
                value={openingPrice}
                onChange={(event) => setOpeningPrice(event.target.value)}
              />
            </label>
            <label>
              Costo totale
              <input
                type="number"
                step="0.01"
                min="0"
                value={openingCost}
                onChange={(event) => setOpeningCost(event.target.value)}
              />
            </label>
          </div>
          {openingHint ? (
            <p className="operation-preview">
              {openingHint.label}{" "}
              {openingHint.label === "Quantità" ? "calcolata" : "calcolato"}:{" "}
              <strong>{openingHint.value}</strong>
            </p>
          ) : (
            <p className="muted small">
              Compila due valori su tre: il terzo viene calcolato.
            </p>
          )}
          {openingError && <p className="error">{openingError}</p>}
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
  const [unitPrice, setUnitPrice] = useState(
    editing?.kind === "opening" ? "" : (editing?.unit_price ?? ""),
  );
  const [totalAmount, setTotalAmount] = useState(
    editing?.kind === "opening" ? (editing?.gross_amount ?? "") : "",
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

  const num = (value: string): number | null => {
    if (value.trim() === "") return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  };
  const qtyValue = num(quantity);
  const priceValue = num(unitPrice);
  const totalValue = num(totalAmount);
  const providedCount = [qtyValue, priceValue, totalValue].filter(
    (value) => value !== null,
  ).length;

  let pairError: string | null = null;
  let derivedLabel = "";
  let derivedValue = "";
  let grossValue = 0;
  if (providedCount === 3) {
    pairError = "Inserisci solo due valori su tre.";
  } else if (providedCount < 2) {
    pairError = "Inserisci due valori tra quantità, prezzo unitario e totale.";
  } else if (qtyValue !== null && priceValue !== null) {
    grossValue = qtyValue * priceValue;
    derivedLabel = "Totale";
    derivedValue = money(String(grossValue));
  } else if (qtyValue !== null && totalValue !== null) {
    grossValue = totalValue;
    derivedLabel = "Prezzo";
    derivedValue =
      qtyValue > 0 ? formatQuantity(String(totalValue / qtyValue)) : "—";
  } else if (priceValue !== null && totalValue !== null) {
    grossValue = totalValue;
    derivedLabel = "Quantità";
    derivedValue =
      priceValue > 0 ? formatQuantity(String(totalValue / priceValue)) : "—";
  }
  const fee = kind === "buy" || kind === "sell" ? Number(commission || 0) : 0;
  const previewTotal =
    kind === "buy" ? grossValue + fee : kind === "sell" ? grossValue - fee : grossValue;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (kind !== "dividend" && pairError) return;
    const payload: InvestmentOperationPayload = {
      kind,
      date,
      description: description.trim(),
    };
    if (kind === "dividend") {
      payload.amount = amount;
    } else {
      if (qtyValue !== null) payload.quantity = quantity;
      if (priceValue !== null) payload.unit_price = unitPrice;
      if (totalValue !== null) payload.total_amount = totalAmount;
      if (kind !== "opening") payload.commission = commission || "0";
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
          <>
            <label>
              Quantità
              <input
                type="number"
                step="any"
                min="0"
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
            </label>
            <label>
              Prezzo unitario
              <input
                type="number"
                step="any"
                min="0"
                value={unitPrice}
                onChange={(event) => setUnitPrice(event.target.value)}
              />
            </label>
            <label>
              Controvalore totale
              <input
                type="number"
                step="0.01"
                min="0"
                value={totalAmount}
                onChange={(event) => setTotalAmount(event.target.value)}
              />
            </label>
            {kind !== "opening" && (
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
            )}
          </>
        )}
      </div>

      {kind !== "dividend" &&
        (pairError ? (
          <p className="error">{pairError}</p>
        ) : (
          <p className="operation-preview">
            Totale: <strong>{money(String(previewTotal))}</strong>
            <span className="muted small">
              {" "}
              · {derivedLabel}{" "}
              {derivedLabel === "Quantità" ? "calcolata" : "calcolato"}:{" "}
              {derivedValue}
            </span>
            {kind === "buy" && (
              <span className="muted small"> · esce dal conto</span>
            )}
            {kind === "sell" && (
              <span className="muted small"> · entra nel conto</span>
            )}
          </p>
        ))}

      <label>
        Descrizione (opzionale)
        <input
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="PAC febbraio, dividendo trimestrale…"
        />
      </label>

      <div className="actions">
        <button type="submit" disabled={busy || (kind !== "dividend" && Boolean(pairError))}>
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
  const [confirmArchive, setConfirmArchive] = useState(false);
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
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await api.updateInvestmentPosition(position.id, { archived: !archived });
      setMessage(archived ? "Posizione riattivata." : "Posizione archiviata.");
      setConfirmArchive(false);
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

  return (
    <section className="card" id="position-detail">
      <div className="card-heading">
        <div>
          <h2>{position.name}</h2>
          <p className="muted small">
            {position.category_label || "Senza categoria"}
            {position.identifier ? ` · ${position.identifier}` : ""}
            {position.archived && (
              <>
                {" "}
                · <span className="badge disabled">Archiviata</span>
              </>
            )}
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
            onClick={() => setConfirmArchive(true)}
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

      <div className="detail-ops-head">
        <h3>Operazioni ({operations.length})</h3>
      </div>
      {loadingDetail ? (
        <SkeletonLines rows={3} label="Caricamento operazioni" />
      ) : operations.length === 0 ? (
        <p className="muted">Nessuna operazione registrata.</p>
      ) : (
        <ul className="entity-list operation-list">
          {operations.map((operation) => {
            const details: string[] = [];
            const quantity =
              operation.quantity === null
                ? ""
                : `${formatQuantity(operation.quantity)} quote`;
            const price =
              operation.unit_price === null
                ? ""
                : `a ${money(operation.unit_price)}`;
            if (quantity || price) {
              details.push([quantity, price].filter(Boolean).join(" "));
            }
            if (operation.kind === "buy" || operation.kind === "sell") {
              details.push(`commissione ${money(operation.commission)}`);
            }
            if (operation.description) details.push(operation.description);
            const cash =
              operation.kind === "opening"
                ? null
                : operation.kind === "buy"
                  ? -Number(operation.cash_amount)
                  : Number(operation.cash_amount);
            return (
              <li className="operation-row" key={operation.id}>
                <div className="operation-main">
                  <strong>
                    {operation.kind_label} · {prettyDate(operation.date)}
                  </strong>
                  {details.length > 0 && (
                    <span className="muted small">{details.join(" · ")}</span>
                  )}
                  {operation.kind === "sell" && (
                    <span className="muted small">
                      Costo rimosso {money(operation.cost_removed)} · plusvalenza{" "}
                      {signedMoney(operation.realized_gain)}
                    </span>
                  )}
                </div>
                {cash !== null && (
                  <span className={cash < 0 ? "negative" : "positive"}>
                    {signedMoney(cash.toFixed(2))}
                  </span>
                )}
                <span className="position-actions">
                  <button
                    type="button"
                    className="secondary small-button"
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
                    className="danger small-button"
                    onClick={() => setConfirmDeleteOperation(operation)}
                    disabled={busy}
                  >
                    Elimina
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {confirmArchive && (
        <ConfirmModal
          title={
            archived
              ? `Riattivare la posizione «${position.name}»?`
              : `Archiviare la posizione «${position.name}»?`
          }
          summary={
            archived
              ? [
                  "Tornerà disponibile per registrare nuove operazioni.",
                  "Lo storico delle operazioni e i saldi restano invariati.",
                ]
              : [
                  "Non potrai registrare nuove operazioni finché non la riattivi.",
                  "Lo storico delle operazioni e i saldi restano invariati.",
                  "La posizione resterà consultabile nell'archivio.",
                ]
          }
          confirmLabel={archived ? "Riattiva" : "Archivia"}
          busyLabel={archived ? "Riattivazione…" : "Archiviazione…"}
          busy={busy}
          onConfirm={() => void toggleArchive()}
          onCancel={() => setConfirmArchive(false)}
        />
      )}
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
  const [savings, setSavings] = useState<SavingsAccount[]>([]);
  const [sourceChoice, setSourceChoice] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [portfolioData, accountsData, savingsData] = await Promise.all([
      api.investments(),
      api.accounts(),
      api.savings(),
    ]);
    setPortfolio(portfolioData);
    setAccounts(accountsData.accounts);
    setSavings(savingsData.savings);
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
    if (portfolio?.investment_savings) {
      setSourceChoice(`savings:${portfolio.investment_savings.id}`);
    } else if (portfolio?.investment_account) {
      setSourceChoice(`account:${portfolio.investment_account.id}`);
    } else {
      setSourceChoice("");
    }
  }, [
    portfolio?.investment_account?.id,
    portfolio?.investment_savings?.id,
  ]);

  useEffect(() => {
    if (
      portfolio &&
      selectedId !== null &&
      !portfolio.positions.some((position) => position.id === selectedId)
    ) {
      setSelectedId(null);
    }
  }, [portfolio, selectedId]);

  useEffect(() => {
    if (selectedId === null && !archiveOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedId(null);
        setArchiveOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [selectedId, archiveOpen]);  async function reload() {
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
      const [kind, rawId] = sourceChoice.split(":");
      const id = rawId ? Number(rawId) : null;
      await api.setInvestmentSource(
        kind === "savings" ? { savings: id } : { account: id },
      );
      setMessage("Fonte degli investimenti aggiornata.");
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

  if (loading) return <LoadingScreen />;

  const summary = portfolio?.summary ?? null;
  const investmentAccount = portfolio?.investment_account ?? null;
  const activeAccounts = accounts.filter(
    (account) =>
      !account.archived ||
      (investmentAccount !== null && account.id === investmentAccount.id),
  );
  const visiblePositions = (portfolio?.positions ?? []).filter(
    (position) => !position.archived,
  );
  const archivedPositions = (portfolio?.positions ?? []).filter(
    (position) => position.archived,
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
            onClick={() => setShowNew((value) => !value)}
            disabled={busy}
          >
            {showNew ? "Chiudi" : "Nuova posizione"}
          </button>
        </div>      </section>

      {message && <p className="notice success">{message}</p>}
      {error && <p className="error">{error}</p>}

      {showNew && (
        <section className="card" id="new-position">
          <h2>Nuova posizione</h2>
          <NewPositionForm
            busy={busy}
            onCreate={createPosition}
            onCancel={() => setShowNew(false)}
          />
        </section>
      )}

      {summary && (
        <section className="card invest-summary">
          <div className="invest-summary-main">
            <span className="stat-label">Valore corrente</span>
            <strong className="dash-big">{money(summary.total_value)}</strong>
            <span className="muted small">
              Costo investito {money(summary.total_cost)}
            </span>
          </div>
          <div className="invest-summary-side">
            <div>
              <span>Plusvalenza non realizzata</span>
              <strong
                className={
                  Number(summary.total_unrealized) < 0 ? "negative" : "positive"
                }
              >
                {signedMoney(summary.total_unrealized)}
              </strong>
            </div>
            <div>
              <span>Plusvalenze realizzate</span>
              <strong
                className={
                  Number(summary.realized_gain) < 0 ? "negative" : "positive"
                }
              >
                {signedMoney(summary.realized_gain)}
              </strong>
            </div>
            <div>
              <span>Dividendi incassati</span>
              <strong>{money(summary.dividends)}</strong>
            </div>
            <div>
              <span>Posizioni senza prezzo</span>
              <strong>{summary.positions_without_price}</strong>
            </div>
          </div>
        </section>
      )}

      <section className="card">
        <div className="card-heading">
          <h2>Posizioni ({visiblePositions.length})</h2>
          {archivedPositions.length > 0 && (
            <button
              type="button"
              className="icon-button"
              title="Posizioni archiviate"
              aria-label="Posizioni archiviate"
              onClick={() => setArchiveOpen(true)}
            >
              <Archive size={16} aria-hidden="true" />
            </button>
          )}
        </div>
        {visiblePositions.length === 0 ? (
          portfolio?.positions.length ? (
            <EmptyState
              illustration="investments"
              title="Nessuna posizione attiva"
              description="Le posizioni archiviate restano consultabili dall'archivio, in alto a destra."
            />
          ) : (
            <EmptyState
              illustration="investments"
              title="Portafoglio vuoto"
              description="Crea la prima posizione per seguire quantità, costi, valore e plusvalenze."
              actionLabel="Nuova posizione"
              onAction={() => {
                setShowNew(true);
                requestAnimationFrame(() => {
                  document
                    .getElementById("new-position")
                    ?.scrollIntoView({ behavior: "smooth", block: "start" });
                });
              }}
            />
          )
        ) : (
          <ul className="entity-list position-list">
            {visiblePositions.map((position) => {
              return (
                <li
                  key={position.id}
                  className={
                    position.id === selectedId ? "position-row selected" : "position-row"
                  }
                >
                  <div className="position-main">
                    <strong>
                      {position.name}
                      {position.identifier && (
                        <span className="muted small">
                          {" "}· {position.identifier}
                        </span>
                      )}
                    </strong>
                    <span className="muted small">
                      {position.category_label || "Senza categoria"} ·{" "}
                      {formatQuantity(position.quantity)} quote · costo medio{" "}
                      {money(position.average_cost)}
                    </span>
                    <span className="muted small">
                      Costo residuo {money(position.cost)} · prezzo{" "}
                      {priceText(position.current_price)}
                      {position.price_updated_on
                        ? ` (${prettyDate(position.price_updated_on)})`
                        : ""}
                    </span>
                  </div>
                  <div className="position-values">
                    <span className="position-total">
                      {priceText(position.current_value)}
                    </span>
                    <span
                      className={
                        position.unrealized_gain === null
                          ? "muted small"
                          : Number(position.unrealized_gain) < 0
                            ? "negative small"
                            : "positive small"
                      }
                    >
                      {position.unrealized_gain === null
                        ? "senza prezzo"
                        : signedMoney(position.unrealized_gain)}
                    </span>
                  </div>
                  <span className="position-actions">
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => setSelectedId(position.id)}
                    >
                      Apri
                    </button>
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </section>

      <details className="card invest-source">
        <summary>
          <span className="invest-source-label">
            <span className="stat-label">Fonte investimenti</span>
            <strong>
              {investmentAccount?.name ??
                portfolio?.investment_savings?.name ??
                "Nessuna"}
            </strong>
          </span>
          <span className="muted small">Modifica</span>
        </summary>
        <form className="investment-account" onSubmit={saveAccount}>
          <label>
            Conto o salvadanaio
            <select
              value={sourceChoice}
              onChange={(event) => setSourceChoice(event.target.value)}
            >
              <option value="">Nessuna fonte</option>
              <optgroup label="Conti">
                {activeAccounts.map((account) => (
                  <option
                    key={`account-${account.id}`}
                    value={`account:${account.id}`}
                  >
                    {account.name}
                  </option>
                ))}
              </optgroup>
              <optgroup label="Salvadanai">
                {savings.map((item) => (
                  <option
                    key={`savings-${item.id}`}
                    value={`savings:${item.id}`}
                  >
                    {item.name} · appoggio {item.backing_account_name}
                  </option>
                ))}
              </optgroup>
            </select>
          </label>
          <button type="submit" disabled={busy}>
            Salva
          </button>
        </form>
        {!investmentAccount && !portfolio?.investment_savings && (
          <p className="notice warning">
            Scegli un conto o un salvadanaio per registrare acquisti, vendite e
            dividendi.
          </p>
        )}
      </details>

      {selectedPosition && (
        <div className="modal-backdrop" onClick={() => setSelectedId(null)}>
          <div
            className="modal modal-wide position-modal"
            role="dialog"
            aria-modal="true"
            aria-label={selectedPosition.name}
            onClick={(event) => event.stopPropagation()}
          >
            <button
              type="button"
              className="modal-close position-modal-close"
              aria-label="Chiudi dettaglio"
              onClick={() => setSelectedId(null)}
            >
              <X size={18} aria-hidden="true" />
            </button>
            <PositionDetail
              key={selectedPosition.id}
              position={selectedPosition}
              onChanged={reload}
              onDeleted={async () => {
                setSelectedId(null);
                await reload();
              }}
            />
          </div>
        </div>
      )}

      {archiveOpen && (
        <div className="modal-backdrop" onClick={() => setArchiveOpen(false)}>
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label="Posizioni archiviate"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="card-heading">
              <h2>Posizioni archiviate</h2>
              <button
                type="button"
                className="modal-close"
                aria-label="Chiudi archivio"
                onClick={() => setArchiveOpen(false)}
              >
                <X size={18} aria-hidden="true" />
              </button>
            </div>
            <ul className="entity-list">
              {archivedPositions.map((position) => (
                <li key={position.id}>
                  <div>
                    <strong>{position.name}</strong>
                    <span className="muted small">
                      {" "}
                      · {position.category_label || "Senza categoria"}
                      {position.identifier ? ` · ${position.identifier}` : ""}
                    </span>
                  </div>
                  <span className="position-actions">
                    <button
                      type="button"
                      className="secondary small-button"
                      onClick={() => {
                        setArchiveOpen(false);
                        setSelectedId(position.id);
                      }}
                    >
                      Apri
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
