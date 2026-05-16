import { useRef, useState, useEffect, useCallback } from "react";

interface BigChartProps {
  data: number[];
  height?: number;
  formatValue?: (v: number) => string;
  formatLabel?: (i: number, total: number) => string;
}

export default function BigChart({
  data,
  height = 280,
  formatValue,
  formatLabel,
}: BigChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(800);
  const [hover, setHover] = useState<{ i: number; x: number; y: number; v: number } | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver((entries) => setW(entries[0].contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const padL = 8,
    padR = 56,
    padT = 8,
    padB = 24;
  const iw = Math.max(50, w - padL - padR);
  const ih = height - padT - padB;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = iw / (data.length - 1);
  const points = data.map((v, i) => [
    padL + i * step,
    padT + ih - ((v - min) / range) * ih,
  ]);
  const d = points
    .map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1))
    .join(" ");
  const first = data[0],
    last = data[data.length - 1];
  const positive = last >= first;
  const color = positive ? "var(--up)" : "var(--down)";
  const gridYs = [0, 0.25, 0.5, 0.75, 1].map((t) => padT + ih * (1 - t));
  const gridVals = [0, 0.25, 0.5, 0.75, 1].map((t) => min + range * t);

  const fmt = formatValue || ((n: number) =>
    "$" + Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n));

  const fmtLabel = formatLabel || ((i: number, total: number) => `Day -${total - 1 - i}`);

  const onMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      const rect = e.currentTarget.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const i = Math.round((x - padL) / step);
      if (i >= 0 && i < data.length) {
        setHover({ i, x: points[i][0], y: points[i][1], v: data[i] });
      }
    },
    [data, points, step],
  );

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <svg
        width={w}
        height={height}
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
        style={{ display: "block", overflow: "visible" }}
      >
        <defs>
          <linearGradient id="chart-fill-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={positive ? "var(--up)" : "var(--down)"} stopOpacity="0.20" />
            <stop offset="100%" stopColor={positive ? "var(--up)" : "var(--down)"} stopOpacity="0" />
          </linearGradient>
        </defs>
        {gridYs.map((y, i) => (
          <g key={i}>
            <line
              x1={padL}
              x2={padL + iw}
              y1={y}
              y2={y}
              stroke="var(--line)"
              strokeWidth="1"
              strokeDasharray={i === 0 ? "" : "2 3"}
            />
            <text
              x={padL + iw + 8}
              y={y + 4}
              fill="var(--fg-3)"
              fontFamily="var(--font-mono)"
              fontSize="11"
            >
              {fmt(gridVals[i])}
            </text>
          </g>
        ))}
        <path
          d={d + ` L ${points[points.length - 1][0]},${padT + ih} L ${points[0][0]},${padT + ih} Z`}
          fill="url(#chart-fill-grad)"
        />
        <path d={d} fill="none" stroke={color} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        {hover && (
          <g>
            <line
              x1={hover.x}
              x2={hover.x}
              y1={padT}
              y2={padT + ih}
              stroke="var(--fg-3)"
              strokeWidth="1"
              strokeDasharray="2 3"
            />
            <circle cx={hover.x} cy={hover.y} r="4" fill="var(--bg-2)" stroke={color} strokeWidth="1.8" />
          </g>
        )}
      </svg>
      {hover && (
        <div
          style={{
            position: "absolute",
            left: Math.min(w - 140, Math.max(0, hover.x - 60)),
            top: 0,
            background: "var(--bg-2)",
            border: "1px solid var(--line-2)",
            borderRadius: "var(--radius)",
            padding: "6px 10px",
            fontSize: 12,
            pointerEvents: "none",
            boxShadow: "0 4px 12px rgba(0,0,0,0.06)",
          }}
        >
          <div className="num" style={{ fontWeight: 600 }}>
            {fmt(hover.v)}
          </div>
          <div style={{ color: "var(--fg-3)", fontSize: 11 }}>{fmtLabel(hover.i, data.length)}</div>
        </div>
      )}
    </div>
  );
}
