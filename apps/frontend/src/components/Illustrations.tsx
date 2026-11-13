import type { ReactElement } from "react";
import {
  Clock,
  PiggyBank,
  ReceiptText,
  Trash2,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from "lucide-react";

/**
 * Icone degli stati vuoti: glifi Lucide, lo stesso set delle icone di navigazione.
 *
 * Il soggetto coincide con l'icona della destinazione (portafoglio per i conti,
 * ricevuta per i movimenti, salvadanaio, andamento, orologio, cestino). Il colore
 * arriva dal contesto: `EmptyState` le colora con l'accento del tema, mentre
 * dimensione e tratto restano allineati alla resa Android (96 px, tratto 1,5 sul
 * viewBox 24×24 di Lucide).
 */
export type IllustrationId =
  | "accounts"
  | "movements"
  | "savings"
  | "investments"
  | "automations"
  | "trash";

type IllustrationComponent = () => ReactElement;

/** Dimensione dell'icona (geometria: stesso valore di `EmptyState.kt`, 96 dp). */
const ART_SIZE = 96;
/** Tratto dichiarato da Lucide per la dimensione grande (identico sul client nativo). */
const ART_STROKE = 1.5;

function Art({ icon: Icon }: { icon: LucideIcon }) {
  return <Icon size={ART_SIZE} strokeWidth={ART_STROKE} />;
}

/** Conti: portafoglio (`wallet`). */
export function AccountsIllustration() {
  return <Art icon={Wallet} />;
}

/** Movimenti: ricevuta con righe (`receipt-text`). */
export function MovementsIllustration() {
  return <Art icon={ReceiptText} />;
}

/** Salvadanai: salvadanaio (`piggy-bank`). */
export function SavingsIllustration() {
  return <Art icon={PiggyBank} />;
}

/** Investimenti: andamento in salita (`trending-up`). */
export function InvestmentsIllustration() {
  return <Art icon={TrendingUp} />;
}

/** Automazioni: orologio (`clock`). */
export function AutomationsIllustration() {
  return <Art icon={Clock} />;
}

/** Cestino: pattumiera (`trash`). */
export function TrashIllustration() {
  return <Art icon={Trash2} />;
}

/** Mappa id → componente, usata da `EmptyState`. */
export const ILLUSTRATIONS: Record<IllustrationId, IllustrationComponent> = {
  accounts: AccountsIllustration,
  movements: MovementsIllustration,
  savings: SavingsIllustration,
  investments: InvestmentsIllustration,
  automations: AutomationsIllustration,
  trash: TrashIllustration,
};
