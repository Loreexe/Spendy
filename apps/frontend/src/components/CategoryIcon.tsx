import {
  BookOpen,
  Briefcase,
  Car,
  Coffee,
  CreditCard,
  Dumbbell,
  Film,
  Fuel,
  Gamepad2,
  Gift,
  GraduationCap,
  HeartPulse,
  House,
  Leaf,
  Music,
  PawPrint,
  PiggyBank,
  Plane,
  Receipt,
  Shirt,
  ShoppingBag,
  ShoppingCart,
  Smartphone,
  Sparkles,
  Stethoscope,
  Tag,
  TrainFront,
  Utensils,
  Wrench,
  type LucideIcon,
} from "lucide-react";

export interface CategoryIconOption {
  /** Nome canonico Lucide usato dal backend (`Category.icon`). */
  name: string;
  /** Etichetta italiana mostrata nella griglia del selettore. */
  label: string;
}

/**
 * Catalogo delle icone delle categorie (DC-117). I nomi coincidono con la
 * whitelist del backend; l'ordine parte dalle predefinite e prosegue con il
 * catalogo extra, come nel brief 0.8.4.
 */
export const CATEGORY_ICONS: CategoryIconOption[] = [
  { name: "tag", label: "Etichetta" },
  { name: "shopping-cart", label: "Carrello" },
  { name: "house", label: "Casa" },
  { name: "car", label: "Auto" },
  { name: "heart-pulse", label: "Salute" },
  { name: "gamepad-2", label: "Gioco" },
  { name: "shopping-bag", label: "Borsa" },
  { name: "briefcase", label: "Lavoro" },
  { name: "piggy-bank", label: "Risparmio" },
  { name: "utensils", label: "Posate" },
  { name: "coffee", label: "Caffè" },
  { name: "plane", label: "Aereo" },
  { name: "train-front", label: "Treno" },
  { name: "fuel", label: "Carburante" },
  { name: "gift", label: "Regalo" },
  { name: "music", label: "Musica" },
  { name: "film", label: "Cinema" },
  { name: "dumbbell", label: "Palestra" },
  { name: "paw-print", label: "Animali" },
  { name: "graduation-cap", label: "Studio" },
  { name: "stethoscope", label: "Medicina" },
  { name: "wrench", label: "Riparazioni" },
  { name: "smartphone", label: "Telefono" },
  { name: "shirt", label: "Abbigliamento" },
  { name: "sparkles", label: "Extra" },
  { name: "receipt", label: "Scontrino" },
  { name: "credit-card", label: "Carta" },
  { name: "book-open", label: "Libri" },
  { name: "leaf", label: "Natura" },
];

const ICON_COMPONENTS: Record<string, LucideIcon> = {
  tag: Tag,
  "shopping-cart": ShoppingCart,
  house: House,
  car: Car,
  "heart-pulse": HeartPulse,
  "gamepad-2": Gamepad2,
  "shopping-bag": ShoppingBag,
  briefcase: Briefcase,
  "piggy-bank": PiggyBank,
  utensils: Utensils,
  coffee: Coffee,
  plane: Plane,
  "train-front": TrainFront,
  fuel: Fuel,
  gift: Gift,
  music: Music,
  film: Film,
  dumbbell: Dumbbell,
  "paw-print": PawPrint,
  "graduation-cap": GraduationCap,
  stethoscope: Stethoscope,
  wrench: Wrench,
  smartphone: Smartphone,
  shirt: Shirt,
  sparkles: Sparkles,
  receipt: Receipt,
  "credit-card": CreditCard,
  "book-open": BookOpen,
  leaf: Leaf,
};

/** Nome dell'icona anche per valori sconosciuti: il fallback è sempre `tag`. */
export function categoryIconName(value?: string | null): string {
  if (value && ICON_COMPONENTS[value]) return value;
  return "tag";
}

/** Etichetta italiana di un nome icona (per testi e tooltip). */
export function categoryIconLabel(value?: string | null): string {
  const name = categoryIconName(value);
  return CATEGORY_ICONS.find((option) => option.name === name)?.label ?? "Etichetta";
}

export function categoryIconComponent(value?: string | null): LucideIcon {
  return ICON_COMPONENTS[categoryIconName(value)];
}

/** Icona Lucide di una categoria; decorativa salvo `title` esplicito. */
export function CategoryIcon({
  name,
  size = 18,
  className,
  title,
}: {
  name?: string | null;
  size?: number;
  className?: string;
  title?: string;
}) {
  const Icon = categoryIconComponent(name);
  return (
    <Icon
      size={size}
      strokeWidth={2}
      className={className ?? "category-icon"}
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      aria-label={title}
      focusable="false"
    />
  );
}
