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
      <div style={{ background: "var(--bg-2)", border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 24 }}>
        <p style={{ color: "var(--fg-3)", fontSize: 13 }}>No allocation data</p>
      </div>
    );
  }

  const actualData = classSummaries.map((s) => ({ name: s.className, value: s.percentage, color: s.color }));
  const targetData = classSummaries
    .filter((s) => s.targetWeight > 0)
    .map((s) => ({ name: s.className, value: s.targetWeight, color: s.color }));

  return (
    <div style={{ background: "var(--bg-2)", border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 24 }}>
      <h4 className="section-title" style={{ marginBottom: 16 }}>Actual vs Target</h4>
      <ResponsiveContainer width="100%" height={380}>
        <PieChart>
          <Pie
            data={actualData}
            cx="50%"
            cy="45%"
            innerRadius="50%"
            outerRadius="90%"
            paddingAngle={1.5}
            dataKey="value"
            stroke="var(--bg)"
            strokeWidth={4}
          >
            {actualData.map((entry, index) => (
              <Cell key={`actual-${index}`} fill={entry.color} opacity={0.85} />
            ))}
          </Pie>
          {targetData.length > 0 && (
            <Pie
              data={targetData}
              cx="50%"
              cy="45%"
              innerRadius="25%"
              outerRadius="47%"
              paddingAngle={1.5}
              dataKey="value"
              stroke="var(--bg)"
              strokeWidth={4}
            >
              {targetData.map((entry, index) => (
                <Cell key={`target-${index}`} fill={entry.color} opacity={0.55} />
              ))}
            </Pie>
          )}
          <Tooltip
            formatter={(value) => `${Number(value).toFixed(1)}%`}
            contentStyle={{
              background: "var(--bg-2)",
              border: "1px solid var(--line)",
              borderRadius: 8,
              color: "var(--fg)",
              fontSize: 12,
            }}
            labelStyle={{ color: "var(--fg)" }}
            itemStyle={{ color: "var(--fg-2)" }}
          />
        </PieChart>
      </ResponsiveContainer>
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
      <div style={{ textAlign: "center", fontSize: 11, color: "var(--fg-3)", marginTop: 10 }}>
        Outer: Actual &middot; Inner: Target
      </div>
    </div>
  );
}
