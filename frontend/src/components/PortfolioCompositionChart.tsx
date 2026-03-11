import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { ChartCard } from "./ChartCard";

interface AllocationEntry {
  class_name: string;
  actual_weight: number;
}

interface PortfolioCompositionChartProps {
  allocation: AllocationEntry[];
}

const COLORS = [
  "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
  "#EC4899", "#14B8A6", "#F97316", "#6366F1", "#84CC16",
];

export function PortfolioCompositionChart({ allocation }: PortfolioCompositionChartProps) {
  const data = allocation.map((a) => ({
    name: a.class_name,
    value: a.actual_weight,
  }));

  if (data.length === 0) {
    return (
      <ChartCard title="Portfolio Composition">
        <p className="text-gray-500 text-sm">No allocation data available</p>
      </ChartCard>
    );
  }

  return (
    <ChartCard title="Portfolio Composition">
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={60}
            outerRadius={100}
            paddingAngle={2}
            dataKey="value"
            label={({ name, value }) => `${name} ${value.toFixed(1)}%`}
          >
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
        </PieChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
