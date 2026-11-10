import type { ReactElement, ReactNode } from "react";

/**
 * Illustrazioni line art per gli stati vuoti (Fase UI).
 *
 * Regole condivise: viewBox 160×150, solo tratto (`fill="none"`,
 * `stroke="currentColor"`, spessore 2, estremi arrotondati). Il colore viene
 * dal contesto: `EmptyState` le colora con l'accento del tema.
 */

/** Id delle illustrazioni disponibili. */
export type IllustrationId =
  | "accounts"
  | "movements"
  | "savings"
  | "investments"
  | "automations"
  | "trash";

type IllustrationComponent = () => ReactElement;

function Frame({ children }: { children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 160 150"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

/** Conti: portafoglio con una moneta. */
export function AccountsIllustration() {
  return (
    <Frame>
      <rect x="30" y="56" width="100" height="64" rx="14" />
      <path d="M30 76h100" />
      <circle cx="108" cy="96" r="6" />
      <circle cx="112" cy="40" r="11" />
      <circle cx="112" cy="40" r="4" />
    </Frame>
  );
}

/** Movimenti: foglio con segno € e freccia. */
export function MovementsIllustration() {
  return (
    <Frame>
      <path d="M46 20h50l22 22v88H46z" />
      <path d="M96 20v22h22" />
      <circle cx="82" cy="76" r="18" />
      <path d="M90 67a12 12 0 1 0 0 18" />
      <path d="M72 72h15M72 80h15" />
      <path d="M60 112h34" />
      <path d="M87 105l7 7-7 7" />
    </Frame>
  );
}

/** Salvadanai: maialino con moneta. */
export function SavingsIllustration() {
  return (
    <Frame>
      <rect x="30" y="60" width="96" height="52" rx="26" />
      <path d="M94 66l8-18 14 14" />
      <path d="M126 74h10a9 9 0 0 1 0 18h-10" />
      <path d="M52 112v14M82 112v14M112 112v14" />
      <path d="M62 70h20" />
      <path d="M30 82c-9-3-12 9-3 12" />
      <circle cx="72" cy="44" r="9" />
    </Frame>
  );
}

/** Investimenti: grafico a barre crescenti. */
export function InvestmentsIllustration() {
  return (
    <Frame>
      <path d="M30 34v78h104" />
      <rect x="48" y="84" width="18" height="28" rx="3" />
      <rect x="78" y="64" width="18" height="48" rx="3" />
      <rect x="108" y="44" width="18" height="68" rx="3" />
    </Frame>
  );
}

/** Automazioni: orologio con freccia circolare. */
export function AutomationsIllustration() {
  return (
    <Frame>
      <circle cx="76" cy="80" r="30" />
      <path d="M76 80V62M76 80h14" />
      <path d="M112 64a40 40 0 0 1 0 32" />
      <path d="M105 89l7 7 7-7" />
    </Frame>
  );
}

/** Cestino: pattumiera con coperchio. */
export function TrashIllustration() {
  return (
    <Frame>
      <path d="M44 46h72" />
      <path d="M68 46v-8a6 6 0 0 1 6-6h12a6 6 0 0 1 6 6v8" />
      <path d="M50 46l6 74a8 8 0 0 0 8 7h32a8 8 0 0 0 8-7l6-74" />
      <path d="M68 66v40M80 66v40M92 66v40" />
    </Frame>
  );
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
