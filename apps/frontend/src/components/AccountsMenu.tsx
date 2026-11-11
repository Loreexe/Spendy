import { useEffect, useRef, useState } from "react";
import { Wallet } from "lucide-react";
import { Link } from "react-router-dom";
import type { Account } from "../api";
import { amountClass, money } from "../format";

/**
 * Popover dei conti aperto dalla card del saldo in Home (0.8.4): elenco con
 * nome, tipo, saldo ed eventuale archiviazione, più il collegamento a tutti
 * i conti. Esc, click esterno e scelta della voce lo chiudono.
 */
export function AccountsMenu({ accounts }: { accounts: Account[] }) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const allAccountsRef = useRef<HTMLAnchorElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent | TouchEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("touchstart", onPointer);
    document.addEventListener("keydown", onKey);
    allAccountsRef.current?.focus();
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("touchstart", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="accounts-menu" ref={wrapperRef}>
      <button
        ref={triggerRef}
        type="button"
        className="icon-button accounts-menu-button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label="Conti e saldi"
        title="Conti e saldi"
        onClick={() => setOpen((current) => !current)}
      >
        <Wallet size={18} aria-hidden="true" focusable="false" />
      </button>

      {open && (
        <div className="accounts-popover" role="dialog" aria-label="Conti e saldi">
          <div className="card-heading">
            <h2>Conti</h2>
          </div>
          {accounts.length === 0 ? (
            <p className="muted small">Nessun conto. Creane uno per iniziare.</p>
          ) : (
            <ul className="accounts-list">
              {accounts.map((account) => (
                <li
                  key={account.id}
                  className={account.archived ? "archived" : undefined}
                >
                  <span className="accounts-item-main">
                    <strong>{account.name}</strong>
                    <span className="muted small">
                      {account.type_label}
                      {account.archived ? " · archiviato" : ""}
                    </span>
                  </span>
                  <span className={amountClass(account.balance)}>
                    {money(account.balance)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <Link
            ref={allAccountsRef}
            className="button secondary accounts-all"
            to="/accounts"
            onClick={() => setOpen(false)}
          >
            Tutti i conti
          </Link>
        </div>
      )}
    </div>
  );
}
