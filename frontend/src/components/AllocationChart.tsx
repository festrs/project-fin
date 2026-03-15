import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";
import { ChartCard } from "./ChartCard";

interface AllocationEntry {
  class_name: string;
  actual_weight?: number;
  target_weight: number;
}

interface AllocationChartProps {
  allocation: AllocationEntry[];
}

export function AllocationChart({ allocation }: AllocationChartProps) {
  if (allocation.length === 0) {
    return (
      <ChartCard title="Target vs Actual Allocation">
        <p className="text-gray-500 text-sm">No allocation data available</p>
      </ChartCard>
    );
  }

  const data = allocation.map((a) => ({
    name: a.class_name,
    Target: a.target_weight,
    Actual: a.actual_weight ?? 0,
  }));

  return (
    <ChartCard title="Target vs Actual Allocation">
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} />
          <YAxis tick={{ fontSize: 12 }} />
          <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
          <Legend />
          <Bar dataKey="Target" fill="#3B82F6" />
          <Bar dataKey="Actual" fill="#10B981" />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}
