import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";

interface ClassAllocation {
  className: string;
  percentage: number;
  targetWeight: number;
  color: string;
}

interface AllocationDonutChartProps {
  classSummaries: ClassAllocation[];
}

export default function AllocationDonutChart({ classSummaries }: AllocationDonutChartProps) {
  if (classSummaries.length === 0) {
    return (
      <div className="rounded-xl p-6" style={{ background: "var(--surface-container-low)" }}>
        <p className="text-text-muted text-sm">No allocation data</p>
      </div>
    );
  }

  const actualData = classSummaries.map((s) => ({ name: s.className, value: s.percentage, color: s.color }));
  const targetData = classSummaries
    .filter((s) => s.targetWeight > 0)
    .map((s) => ({ name: s.className, value: s.targetWeight, color: s.color }));

  return (
    <div className="rounded-xl p-6" style={{ background: "var(--surface-container-low)" }}>
      <h4
        className="text-xs text-on-surface-variant font-medium uppercase tracking-widest mb-4"
        style={{ fontFamily: "var(--font-family-body)" }}
      >
        Allocation Comparison (Actual vs Target)
      </h4>
      <ResponsiveContainer width="100%" height={320}>
        <PieChart>
          {/* Outer ring: Actual allocation */}
          <Pie
            data={actualData}
            cx="50%"
            cy="50%"
            innerRadius={85}
            outerRadius={120}
            paddingAngle={1}
            dataKey="value"
          >
            {actualData.map((entry, index) => (
              <Cell key={`actual-${index}`} fill={entry.color} />
            ))}
          </Pie>
          {/* Inner ring: Target allocation */}
          {targetData.length > 0 && (
            <Pie
              data={targetData}
              cx="50%"
              cy="50%"
              innerRadius={50}
              outerRadius={80}
              paddingAngle={1}
              dataKey="value"
              opacity={0.5}
            >
              {targetData.map((entry, index) => (
                <Cell key={`target-${index}`} fill={entry.color} />
              ))}
            </Pie>
          )}
          <Tooltip
            formatter={(value) => `${Number(value).toFixed(1)}%`}
            contentStyle={{
              background: "var(--surface-container-high)",
              border: "1px solid var(--glass-border)",
              borderRadius: "var(--radius-sm)",
              color: "var(--color-on-surface)",
              fontSize: "0.75rem",
            }}
          />
          <Legend
            formatter={(value) => (
              <span className="text-xs text-on-surface-variant" style={{ fontFamily: "var(--font-family-body)" }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="text-center text-xs text-text-muted -mt-2 tabular-nums" style={{ fontFamily: "var(--font-family-body)" }}>
        Outer: Actual &middot; Inner: Target
      </div>
    </div>
  );
}
