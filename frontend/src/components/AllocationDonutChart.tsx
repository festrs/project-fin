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
      <div
        className="rounded-xl p-6"
        style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
      >
        <p style={{ color: "var(--text-tertiary)", fontSize: "0.875rem" }}>No allocation data</p>
      </div>
    );
  }

  const actualData = classSummaries.map((s) => ({ name: s.className, value: s.percentage, color: s.color }));
  const targetData = classSummaries
    .filter((s) => s.targetWeight > 0)
    .map((s) => ({ name: s.className, value: s.targetWeight, color: s.color }));

  return (
    <div
      className="rounded-xl p-6"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <h4
        className="text-label"
        style={{
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          color: "var(--text-tertiary)",
          marginBottom: 16,
        }}
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
              legendType="none"
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
              background: "#1c1c1e",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 8,
              color: "#f5f5f7",
              fontSize: "0.75rem",
            }}
            labelStyle={{ color: "#f5f5f7" }}
            itemStyle={{ color: "rgba(255,255,255,0.55)" }}
          />
          <Legend
            formatter={(value) => (
              <span style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)" }}>
                {value}
              </span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
      <div
        className="text-center tabular-nums"
        style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.35)", marginTop: -8 }}
      >
        Outer: Actual &middot; Inner: Target
      </div>
    </div>
  );
}
