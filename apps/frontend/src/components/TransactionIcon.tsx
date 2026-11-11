import { ArrowDownLeft, ArrowLeftRight, ArrowUpRight, Wallet } from "lucide-react";
import type { TransactionKind } from "../api";
import type { Transaction } from "../api";
import { CategoryIcon } from "./CategoryIcon";

/**
 * Icona che apre una riga di movimento: l'icona della categoria quando c'è,
 * altrimenti un'icona neutra coerente col tipo di movimento.
 */
export function TransactionIcon({
  transaction,
  size = 20,
}: {
  transaction: Transaction;
  size?: number;
}) {
  if (transaction.category) {
    return (
      <CategoryIcon
        name={transaction.category.icon}
        size={size}
        title={transaction.category.name}
      />
    );
  }
  switch (transaction.kind) {
    case "income":
      return <ArrowDownLeft size={size} aria-hidden="true" />;
    case "expense":
      return <ArrowUpRight size={size} aria-hidden="true" />;
    case "transfer":
      return <ArrowLeftRight size={size} aria-hidden="true" />;
    default:
      return <Wallet size={size} aria-hidden="true" />;
  }
}


/** Icona del tipo di movimento, usata nelle righe compatte della Home. */
export function MovementKindIcon({
  kind,
  size = 16,
}: {
  kind: TransactionKind;
  size?: number;
}) {
  switch (kind) {
    case "income":
      return <ArrowDownLeft size={size} aria-hidden="true" />;
    case "expense":
      return <ArrowUpRight size={size} aria-hidden="true" />;
    case "transfer":
      return <ArrowLeftRight size={size} aria-hidden="true" />;
    default:
      return <Wallet size={size} aria-hidden="true" />;
  }
}
