import {
  useEffect,
  useId,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import { Check, ChevronDown } from "lucide-react";

export interface AppSelectOption {
  value: string;
  label: string;
  detail?: string;
  icon?: ReactNode;
}

/** Selettore in stile app (listbox) per conti e salvadanai. */
export function AppSelect({
  options,
  value,
  onChange,
  placeholder = "Seleziona…",
  ariaLabel,
  disabled = false,
  emptyOption,
}: {
  options: AppSelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  ariaLabel: string;
  disabled?: boolean;
  emptyOption?: AppSelectOption;
}) {
  const listId = useId();
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  const allOptions: AppSelectOption[] = emptyOption ? [emptyOption, ...options] : options;
  const selected = allOptions.find((option) => option.value === value);
  const selectedIndex = allOptions.findIndex((option) => option.value === value);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent | TouchEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("touchstart", onPointer);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("touchstart", onPointer);
    };
  }, [open]);

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
    const option = allOptions[index];
    if (!option) return;
    onChange(option.value);
    setOpen(false);
    triggerRef.current?.focus();
  }

  function onListKeyDown(event: ReactKeyboardEvent<HTMLUListElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((current) => Math.min(current + 1, allOptions.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((current) => Math.max(current - 1, 0));
    } else if (event.key === "Home") {
      event.preventDefault();
      setActive(0);
    } else if (event.key === "End") {
      event.preventDefault();
      setActive(allOptions.length - 1);
    } else if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      choose(active);
    } else if (event.key === "Escape" || event.key === "Tab") {
      if (event.key === "Escape") {
        event.preventDefault();
        setOpen(false);
        triggerRef.current?.focus();
      } else {
        setOpen(false);
      }
    }
  }

  return (
    <div className="app-select" ref={wrapperRef}>
      <button
        ref={triggerRef}
        type="button"
        className="app-select-trigger"
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
        <span className="app-select-label">
          {selected?.label ?? placeholder}
        </span>
        <ChevronDown size={16} aria-hidden="true" className="app-select-chevron" />
      </button>
      {open && (
        <ul
          id={listId}
          ref={listRef}
          className="app-select-list"
          role="listbox"
          aria-label={ariaLabel}
          tabIndex={-1}
          aria-activedescendant={`${listId}-${active}`}
          onKeyDown={onListKeyDown}
        >
          {allOptions.map((option, index) => (
            <li
              key={option.value || "empty"}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={option.value === value}
              className={`app-select-option${index === active ? " active" : ""}`}
              onMouseEnter={() => setActive(index)}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(index);
              }}
            >
              {option.icon}
              <span className="app-select-option-main">{option.label}</span>
              {option.detail && (
                <span className="app-select-option-detail">{option.detail}</span>
              )}
              {option.value === value && (
                <Check size={15} aria-hidden="true" className="app-select-check" />
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
