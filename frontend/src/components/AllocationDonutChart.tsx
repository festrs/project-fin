import { useState } from "react";

interface ClassAllocation {
  className: string;
  percentage: number;
  targetWeight: number;
  color: string;
}

interface AllocationDonutChartProps {
  classSummaries: ClassAllocation[];
}

const CIRCUMFERENCE = 2 * Math.PI * 44; // outer ring radius
const INNER_CIRCUMFERENCE = 2 * Math.PI * 32; // inner ring radius

export default function AllocationDonutChart({ classSummaries }: AllocationDonutChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (classSummaries.length === 0) {
    return (
      <div className="bg-surface-low rounded-xl p-6">
        <p className="text-text-muted text-sm">No allocation data</p>
      </div>
    );
  }

  // Compute stroke-dasharray and offset for each segment
  const outerSegments = classSummaries.map((s, i) => {
    const dash = (s.percentage / 100) * CIRCUMFERENCE;
    const offset = classSummaries
      .slice(0, i)
      .reduce((sum, prev) => sum + (prev.percentage / 100) * CIRCUMFERENCE, 0);
    return { dash, offset, ...s };
  });

  const innerSegments = classSummaries.map((s, i) => {
    const dash = (s.targetWeight / 100) * INNER_CIRCUMFERENCE;
    const offset = classSummaries
      .slice(0, i)
      .reduce((sum, prev) => sum + (prev.targetWeight / 100) * INNER_CIRCUMFERENCE, 0);
    return { dash, offset, ...s };
  });

  return (
    <div className="bg-surface-low rounded-xl p-6">
      <h4 className="text-xs text-on-surface-variant font-medium uppercase tracking-widest mb-8"
        style={{ fontFamily: "var(--font-family-body)" }}
      >
        Allocation Comparison
      </h4>
      <div className="flex flex-col items-center">
        {/* Donut Chart */}
        <div className="relative w-64 h-64 mb-8">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 100 100">
            {/* Inner ring background */}
            <circle cx="50" cy="50" r="32" fill="transparent" stroke="var(--color-surface-highest)" strokeWidth="12" />
            {/* Inner ring segments (target) */}
            {innerSegments.map((seg, i) => (
              <circle
                key={`inner-${i}`}
                cx="50" cy="50" r="32"
                fill="transparent"
                stroke={seg.color}
                strokeWidth="12"
                strokeDasharray={`${seg.dash} ${INNER_CIRCUMFERENCE - seg.dash}`}
                strokeDashoffset={-seg.offset}
                opacity={0.4}
              />
            ))}
            {/* Outer ring background */}
            <circle cx="50" cy="50" r="44" fill="transparent" stroke="var(--color-surface-highest)" strokeWidth="12" />
            {/* Outer ring segments (actual) */}
            {outerSegments.map((seg, i) => (
              <circle
                key={`outer-${i}`}
                cx="50" cy="50" r="44"
                fill="transparent"
                stroke={seg.color}
                strokeWidth="12"
                strokeDasharray={`${seg.dash} ${CIRCUMFERENCE - seg.dash}`}
                strokeDashoffset={-seg.offset}
                className="cursor-pointer transition-opacity"
                opacity={hoveredIndex !== null && hoveredIndex !== i ? 0.4 : 1}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            ))}
          </svg>
        </div>

        {/* Legend */}
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-3">
          {classSummaries.map((s, i) => (
            <div
              key={s.className}
              className="flex items-center gap-2 cursor-default"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: s.color }} />
              <span className="text-xs font-medium text-on-surface" style={{ fontFamily: "var(--font-family-body)" }}>
                {s.className}
              </span>
              {hoveredIndex === i && (
                <span className="text-[10px] text-on-surface-variant" style={{ fontFamily: "var(--font-family-body)" }}>
                  <span style={{ color: s.color }} className="font-bold">{s.percentage.toFixed(1)}%</span>
                  {" / "}
                  {s.targetWeight.toFixed(0)}%
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
