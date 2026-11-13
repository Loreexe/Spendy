import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Calendar, Clock, X } from "lucide-react";

const MONTHS = [
  "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
  "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
];
const WEEKDAYS = ["L", "M", "M", "G", "V", "S", "D"];

function parseISO(value: string): { y: number; m: number; d: number } | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  return { y: Number(match[1]), m: Number(match[2]) - 1, d: Number(match[3]) };
}

function isoDate(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function DateField({
  value,
  onChange,
  ariaLabel = "Data",
}: {
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const initial = parseISO(value) ?? { y: new Date().getFullYear(), m: new Date().getMonth(), d: new Date().getDate() };
  const [view, setView] = useState({ y: initial.y, m: initial.m });
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);

  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const width = 320;
      setCoords({
        top: rect.bottom + 8,
        left: Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)),
      });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const parsed = parseISO(value);
    if (parsed) setView({ y: parsed.y, m: parsed.m });
    const onOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!wrapperRef.current?.contains(target) && !popoverRef.current?.contains(target)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("keydown", onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const selected = parseISO(value);
  const daysInMonth = new Date(view.y, view.m + 1, 0).getDate();
  const start = (new Date(view.y, view.m, 1).getDay() + 6) % 7;

  function move(delta: number) {
    const next = new Date(view.y, view.m + delta, 1);
    setView({ y: next.getFullYear(), m: next.getMonth() });
  }

  function choose(day: number) {
    onChange(isoDate(view.y, view.m, day));
    setOpen(false);
  }

  return (
    <div className="dt-field" ref={wrapperRef}>
      <span className="dt-label">{ariaLabel}</span>
      <button
        ref={triggerRef}
        type="button"
        className="dt-trigger"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((current) => !current)}
      >
        <Calendar size={17} aria-hidden="true" />
        <span>{value ? value.split("-").reverse().join("/") : "Scegli data"}</span>
      </button>
      {open && coords && createPortal(
        <div
          ref={popoverRef}
          className="dt-popover dt-popover-portal"
          role="dialog"
          aria-label="Calendario"
          style={{ top: coords.top, left: coords.left }}
        >
          <div className="dt-popover-head">
            <div className="dt-nav">
              <button type="button" className="dt-nav-btn" aria-label="Anno precedente" onClick={() => move(-12)}>«</button>
              <button type="button" className="dt-nav-btn" aria-label="Mese precedente" onClick={() => move(-1)}>‹</button>
              <strong>{MONTHS[view.m]} {view.y}</strong>
              <button type="button" className="dt-nav-btn" aria-label="Mese successivo" onClick={() => move(1)}>›</button>
              <button type="button" className="dt-nav-btn" aria-label="Anno successivo" onClick={() => move(12)}>»</button>
            </div>
            <button type="button" className="dt-close" aria-label="Chiudi" onClick={() => setOpen(false)}>
              <X size={16} aria-hidden="true" />
            </button>
          </div>
          <div className="dt-calendar">
            {WEEKDAYS.map((day, index) => (
              <span key={`${day}-${index}`} className="dt-weekday">{day}</span>
            ))}
            {Array.from({ length: start }, (_, index) => (
              <span key={`empty-${index}`} />
            ))}
            {Array.from({ length: daysInMonth }, (_, index) => {
              const day = index + 1;
              const isSelected = selected?.y === view.y && selected.m === view.m && selected.d === day;
              return (
                <button
                  key={day}
                  type="button"
                  className={`dt-day${isSelected ? " selected" : ""}`}
                  aria-pressed={isSelected}
                  onClick={() => choose(day)}
                >
                  {day}
                </button>
              );
            })}
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}

export function TimeField({
  value,
  onChange,
  ariaLabel = "Ora",
}: {
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
}) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const hourRef = useRef<HTMLDivElement | null>(null);
  const minuteRef = useRef<HTMLDivElement | null>(null);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const hour = Number(value.slice(0, 2)) || 0;
  const minute = Number(value.slice(3, 5)) || 0;

  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      const width = 320;
      setCoords({
        top: rect.bottom + 8,
        left: Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8)),
      });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onOutside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!wrapperRef.current?.contains(target) && !popoverRef.current?.contains(target)) setOpen(false);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onOutside);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onOutside);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const scrollToSelected = (container: HTMLDivElement | null, selector: string) => {
      const selected = container?.querySelector<HTMLElement>(selector);
      if (selected && container) {
        container.scrollTop = Math.max(0, selected.offsetTop - container.clientHeight / 2 + selected.offsetHeight / 2);
      }
    };
    scrollToSelected(hourRef.current, "[data-hour].selected");
    scrollToSelected(minuteRef.current, "[data-minute].selected");
  }, [open, hour, minute]);

  function setTime(nextHour: number, nextMinute: number) {
    onChange(`${String(nextHour).padStart(2, "0")}:${String(nextMinute).padStart(2, "0")}`);
  }

  return (
    <div className="dt-field" ref={wrapperRef}>
      <span className="dt-label">{ariaLabel}</span>
      <button
        ref={triggerRef}
        type="button"
        className="dt-trigger"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => setOpen((current) => !current)}
      >
        <Clock size={17} aria-hidden="true" />
        <span>{value || "Scegli ora"}</span>
      </button>
      {open && coords && createPortal(
        <div
          ref={popoverRef}
          className="dt-popover dt-time-popover dt-popover-portal"
          role="dialog"
          aria-label="Orario"
          style={{ top: coords.top, left: coords.left }}
        >
          <div className="dt-popover-head">
            <strong>Orario</strong>
            <button type="button" className="dt-close" aria-label="Chiudi" onClick={() => setOpen(false)}>
              <X size={16} aria-hidden="true" />
            </button>
          </div>
          <div className="dt-time-columns">
            <div className="dt-time-column">
              <span className="dt-time-title">Ore</span>
              <div className="dt-time-scroll" ref={hourRef}>
                {Array.from({ length: 24 }, (_, index) => (
                  <button
                    key={index}
                    type="button"
                    data-hour
                    className={index === hour ? "selected" : ""}
                    aria-pressed={index === hour}
                    onClick={() => setTime(index, minute)}
                  >
                    {String(index).padStart(2, "0")}
                  </button>
                ))}
              </div>
            </div>
            <div className="dt-time-column">
              <span className="dt-time-title">Minuti</span>
              <div className="dt-time-scroll" ref={minuteRef}>
                {Array.from({ length: 60 }, (_, index) => (
                  <button
                    key={index}
                    type="button"
                    data-minute
                    className={index === minute ? "selected" : ""}
                    aria-pressed={index === minute}
                    onClick={() => setTime(hour, index)}
                  >
                    {String(index).padStart(2, "0")}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="dt-time-actions">
            <button type="button" onClick={() => setTime(new Date().getHours(), new Date().getMinutes())}>Ora</button>
            <button type="button" onClick={() => setTime(0, 0)}>Azzera</button>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
