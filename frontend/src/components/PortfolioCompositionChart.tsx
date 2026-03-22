import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { ChartCard } from "./ChartCard";

interface ClassData {
  className: string;
  percentage: number;
  targetWeight: number;
}

interface PortfolioCompositionChartProps {
  allocation?: { class_name: string; actual_weight: number; target_weight?: number }[];
  classSummaries?: ClassData[];
}

const COLORS = [
  "#1e3a5f", "#16a34a", "#d97706", "#2563eb", "#7c3aed",
  "#ec4899", "#0ea5e9", "#f97316", "#475569", "#84cc16",
];

export function PortfolioCompositionChart({ allocation, classSummaries }: PortfolioCompositionChartProps) {
  // Build data from classSummaries (preferred) or allocation (legacy)
  let actualData: { name: string; value: number }[] = [];
  let targetData: { name: string; value: number }[] = [];

  if (classSummaries && classSummaries.length > 0) {
    actualData = classSummaries.map((s) => ({ name: s.className, value: s.percentage }));
    targetData = classSummaries
      .filter((s) => s.targetWeight > 0)
      .map((s) => ({ name: s.className, value: s.targetWeight }));
  } else if (allocation && allocation.length > 0) {
    actualData = allocation.map((a) => ({ name: a.class_name, value: a.actual_weight }));
    targetData = allocation
      .filter((a) => (a.target_weight ?? 0) > 0)
      .map((a) => ({ name: a.class_name, value: a.target_weight ?? 0 }));
  }

  if (actualData.length === 0) {
    return (
      <ChartCard title="Position vs Target">
        <p className="text-text-muted text-base">No allocation data available</p>
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Position vs Target">
      <ResponsiveContainer width="100%" height={350}>
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
            {actualData.map((_entry, index) => (
              <Cell key={`actual-${index}`} fill={COLORS[index % COLORS.length]} />
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
              opacity={0.6}
            >
              {targetData.map((_entry, index) => {
                const actualIdx = actualData.findIndex((a) => a.name === _entry.name);
                return (
                  <Cell
                    key={`target-${index}`}
                    fill={COLORS[(actualIdx >= 0 ? actualIdx : index) % COLORS.length]}
                  />
                );
              })}
            </Pie>
          )}
          <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
          <Legend
            formatter={(value) => <span className="text-base text-on-surface-variant">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
      <div className="text-center text-base text-text-muted -mt-2 tabular-nums">
        Outer: Actual &middot; Inner: Target
      </div>
    </ChartCard>
  );
}
