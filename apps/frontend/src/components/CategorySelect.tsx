import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import { ChevronDown, Tag } from "lucide-react";
import type { Category } from "../api";
import { CategoryIcon } from "./CategoryIcon";

interface CategoryOption {
  id: string;
  name: string;
  icon: string | null;
}

/**
 * Selettore di categoria accessibile (listbox) con le icone del catalogo
 * DC-117. Usato nel form dei movimenti e nei filtri del registro.
 */
export function CategorySelect({
  categories,
  value,
  onChange,
  emptyLabel = "Tutte le categorie",
  ariaLabel,
  disabled = false,
}: {
  categories: Category[];
  value: string;
  onChange: (value: string) => void;
  emptyLabel?: string;
  ariaLabel: string;
  disabled?: boolean;
}) {
  const listId = useId();
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const options: CategoryOption[] = [
    { id: "", name: emptyLabel, icon: null },
    ...categories.map((category) => ({
      id: String(category.id),
      name: category.name,
      icon: category.icon ?? null,
    })),
  ];
  const selectedIndex = options.findIndex((option) => option.id === value);
  const selected = options[selectedIndex >= 0 ? selectedIndex : 0];

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent | TouchEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("touchstart", onPointer);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("touchstart", onPointer);
    };
  }, [open]);

  // Aprendo, il focus entra nella listbox e parte dall'opzione selezionata.
  useEffect(() => {
    if (!open) return;
    setActive(Math.max(selectedIndex, 0));
    listRef.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const option = listRef.current?.children[active] as HTMLElement | undefined;
    option?.scrollIntoView({ block: "nearest" });
  }, [open, active]);

  function choose(index: number) {
    const option = options[index];
    if (!option) return;
    onChange(option.id);
    setOpen(false);
    triggerRef.current?.focus();
  }

  function handleListKeyDown(event: ReactKeyboardEvent<HTMLUListElement>) {
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        setActive((current) => Math.min(current + 1, options.length - 1));
        break;
      case "ArrowUp":
        event.preventDefault();
        setActive((current) => Math.max(current - 1, 0));
        break;
      case "Home":
        event.preventDefault();
        setActive(0);
        break;
      case "End":
        event.preventDefault();
        setActive(options.length - 1);
        break;
      case "Enter":
      case " ":
        event.preventDefault();
        choose(active);
        break;
      case "Escape":
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
        break;
      case "Tab":
        setOpen(false);
        triggerRef.current?.focus();
        break;
      default:
        break;
    }
  }

  return (
    <div className="category-select" ref={wrapperRef}>
      <button
        ref={triggerRef}
        type="button"
        className="category-select-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={ariaLabel}
        disabled={disabled}
        onClick={() => setOpen((current) => !current)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            setOpen(true);
          }
        }}
      >
        <CategoryIcon name={selected.icon} size={16} />
        <span className="category-select-label">{selected.name}</span>
        <ChevronDown
          className="category-select-chevron"
          size={16}
          aria-hidden="true"
          focusable="false"
        />
      </button>

      {open && (
        <ul
          id={listId}
          ref={listRef}
          className="category-select-list"
          role="listbox"
          aria-label={ariaLabel}
          tabIndex={-1}
          aria-activedescendant={`${listId}-${active}`}
          onKeyDown={handleListKeyDown}
        >
          {options.map((option, index) => (
            <li
              key={option.id || "all"}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={option.id === value}
              className={`category-select-option${index === active ? " active" : ""}`}
              onMouseEnter={() => setActive(index)}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(index);
              }}
            >
              {option.icon ? (
                <CategoryIcon name={option.icon} size={16} />
              ) : (
                <Tag
                  className="category-icon"
                  size={16}
                  aria-hidden="true"
                  focusable="false"
                />
              )}
              <span>{option.name}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
