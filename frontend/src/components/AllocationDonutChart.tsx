import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";

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
        Actual vs Target
      </h4>
      <ResponsiveContainer width="100%" height={380}>
        <PieChart>
          {/* Outer ring: Actual allocation */}
          <Pie
            data={actualData}
            cx="50%"
            cy="45%"
            innerRadius="52%"
            outerRadius="90%"
            paddingAngle={2}
            dataKey="value"
            stroke="#0a0a0a"
            strokeWidth={3}
          >
            {actualData.map((entry, index) => (
              <Cell key={`actual-${index}`} fill={entry.color} opacity={0.85} />
            ))}
          </Pie>
          {/* Inner ring: Target allocation */}
          {targetData.length > 0 && (
            <Pie
              data={targetData}
              cx="50%"
              cy="45%"
              innerRadius="25%"
              outerRadius="48%"
              paddingAngle={2}
              dataKey="value"
              stroke="#0a0a0a"
              strokeWidth={3}
            >
              {targetData.map((entry, index) => (
                <Cell key={`target-${index}`} fill={entry.color} opacity={0.55} />
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
        </PieChart>
      </ResponsiveContainer>
      {/* Pill badge legend */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center", marginTop: -4 }}>
        {actualData.map((entry) => (
          <span
            key={entry.name}
            style={{
              display: "inline-flex",
              alignItems: "center",
              padding: "3px 10px",
              borderRadius: "var(--radius-pill)",
              fontSize: 11,
              fontWeight: 600,
              background: entry.color,
              color: "#fff",
              whiteSpace: "nowrap",
            }}
          >
            {entry.name}
          </span>
        ))}
      </div>
      <div
        className="text-center"
        style={{ fontSize: 11, color: "var(--text-tertiary)", marginTop: 10 }}
      >
        Outer: Actual &middot; Inner: Target
      </div>
    </div>
  );
}
