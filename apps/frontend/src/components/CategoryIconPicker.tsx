import {
  CATEGORY_ICONS,
  categoryIconComponent,
  categoryIconLabel,
  categoryIconName,
} from "./CategoryIcon";

/**
 * Griglia del catalogo icone delle categorie (DC-117): radio accessibile,
 * etichette italiane, bersagli da 44 px.
 */
export function CategoryIconPicker({
  value,
  onChange,
  label = "Icona",
}: {
  value?: string | null;
  onChange: (name: string) => void;
  label?: string;
}) {
  const selectedName = categoryIconName(value);
  return (
    <div className="icon-picker">
      <span className="icon-picker-label">
        {label} · {categoryIconLabel(selectedName)}
      </span>
      <div className="icon-picker-grid" role="radiogroup" aria-label={label}>
        {CATEGORY_ICONS.map((option) => {
          const Icon = categoryIconComponent(option.name);
          const selected = selectedName === option.name;
          return (
            <button
              key={option.name}
              type="button"
              role="radio"
              aria-checked={selected}
              aria-label={option.label}
              title={option.label}
              className={`icon-choice${selected ? " selected" : ""}`}
              onClick={() => onChange(option.name)}
            >
              <Icon size={18} strokeWidth={2} aria-hidden="true" focusable="false" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
