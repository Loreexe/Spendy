import { ArrowDownLeft, ArrowUpRight } from "lucide-react";
import { money } from "../format";

export interface SeriesPoint {
  date: string;
  saldo: string;
  patrimonio: string;
}

export interface CategoryTotal {
  id: number;
  name: string;
  total: string;
}

/** Etichetta compatta per le assi: stessa lingua e stesso separatore di money(). */
function shortEuro(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1000) {
    return `${(value / 1000).toLocaleString("it-IT", {
      maximumFractionDigits: 1,
    })}k\u00A0€`;
  }
  return `${value.toLocaleString("it-IT", { maximumFractionDigits: 0 })}\u00A0€`;
}

function shortDate(iso: string): string {
  const [, m, d] = iso.split("-");
  return `${d}/${m}`;
}

export function TrendChart({ points }: { points: SeriesPoint[] }) {
  if (points.length < 2) {
    return (
      <p className="muted">Dati insufficienti per il grafico di andamento.</p>
    );
  }
  const W = 640;
  const H = 220;
  const PAD_L = 56;
  const PAD_B = 22;
  const PAD_T = 10;
  const values = points.flatMap((p) => [Number(p.saldo), Number(p.patrimonio)]);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min -= 1;
    max += 1;
  }
  const span = max - min || 1;
  const iw = W - PAD_L - 8;
  const ih = H - PAD_T - PAD_B;
  const x = (i: number) =>
    PAD_L + (points.length === 1 ? 0 : (i / (points.length - 1)) * iw);
  const y = (v: number) => PAD_T + (1 - (v - min) / span) * ih;
  const line = (pick: (p: SeriesPoint) => number) =>
    points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(pick(p)).toFixed(1)}`).join(" ");
  const ticks = [0, 1, 2, 3].map((i) => min + (span * i) / 3);
  const mid = points[Math.floor(points.length / 2)];
  return (
    <figure className="chart" style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label="Andamento del saldo e del patrimonio nel periodo"
        style={{ width: "100%", height: "auto", display: "block" }}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD_L}
              x2={W - 8}
              y1={y(t)}
              y2={y(t)}
              stroke="var(--line)"
              strokeWidth={1}
            />
            <text
              x={PAD_L - 6}
              y={y(t) + 4}
              textAnchor="end"
              fontSize={11}
              fill="var(--muted)"
            >
              {shortEuro(t)}
            </text>
          </g>
        ))}
        <polyline
          points={points.map((p, i) => `${x(i).toFixed(1)},${y(Number(p.patrimonio)).toFixed(1)}`).join(" ")}
          fill="none"
          stroke="var(--muted)"
          strokeWidth={2}
          strokeDasharray="5 3"
        />
        <path
          d={line((p) => Number(p.saldo))}
          fill="none"
          stroke="var(--accent)"
          strokeWidth={2.5}
          strokeLinejoin="round"
        />
        {points.map((p, i) =>
          i === 0 || i === points.length - 1 ? (
            <text
              key={p.date}
              x={i === 0 ? PAD_L : W - 8}
              y={H - 6}
              textAnchor={i === 0 ? "start" : "end"}
              fontSize={11}
              fill="var(--muted)"
            >
              {shortDate(p.date)}
            </text>
          ) : null,
        )}
        <text
          x={(x(0) + x(points.length - 1)) / 2}
          y={H - 6}
          textAnchor="middle"
          fontSize={11}
          fill="var(--muted)"
        >
          {shortDate(mid.date)}
        </text>
      </svg>
      <figcaption className="muted small">
        <span style={{ color: "var(--accent)" }}>— Saldo totale</span>
        {" · "}
        <span style={{ color: "var(--muted)" }}>- - Patrimonio</span>
      </figcaption>
    </figure>
  );
}

export function InOutBars({
  income,
  expense,
}: {
  income: string;
  expense: string;
}) {
  const inc = Number(income);
  const exp = Number(expense);
  const total = inc + exp;
  const incShare = total > 0 ? (inc / total) * 100 : 0;
  const expShare = total > 0 ? (exp / total) * 100 : 0;
  const pct = (value: number) =>
    `${value.toLocaleString("it-IT", { maximumFractionDigits: 0 })}%`;
  return (
    <div className="inout">
      <div className="inout-cards">
        <div className="inout-card up">
          <span className="inout-card-head">
            <ArrowDownLeft size={14} aria-hidden="true" /> Entrate
          </span>
          <strong>{money(inc)}</strong>
          <span className="muted">{pct(incShare)} del totale</span>
        </div>
        <div className="inout-card down">
          <span className="inout-card-head">
            <ArrowUpRight size={14} aria-hidden="true" /> Uscite
          </span>
          <strong>{money(exp)}</strong>
          <span className="muted">{pct(expShare)} del totale</span>
        </div>
      </div>
      <div
        className="inout-track"
        role="img"
        aria-label={`Entrate ${pct(incShare)}, uscite ${pct(expShare)}`}
      >
        <div className="inout-seg up" style={{ width: `${incShare}%` }} />
        <div className="inout-seg down" style={{ width: `${expShare}%` }} />
      </div>
    </div>
  );
}

export function CategoryBars({ rows }: { rows: CategoryTotal[] }) {
  if (rows.length === 0) {
    return <p className="muted">Nessuna spesa nel periodo.</p>;
  }
  const max = Math.max(...rows.map((r) => Number(r.total)), 1);
  return (
    <div className="chart-bars">
      {rows.map((row) => (
        <div key={row.id} className="chart-bar-row">
          <span className="chart-bar-label">{row.name}</span>
          <div
            className="chart-bar-track"
            role="img"
            aria-label={`${row.name}: ${money(row.total)}`}
          >
            <div
              className="chart-bar-fill"
              style={{
                width: `${(Number(row.total) / max) * 100}%`,
                background: "var(--accent)",
              }}
            />
          </div>
          <strong className="chart-bar-value">{money(row.total)}</strong>
        </div>
      ))}
    </div>
  );
}
