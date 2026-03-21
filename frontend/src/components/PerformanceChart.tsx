import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { ChartCard } from "./ChartCard";
import api from "../services/api";

interface PerformanceEntry {
  date: string;
  value: number;
}

export function PerformanceChart() {
  const [data, setData] = useState<PerformanceEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ holdings: PerformanceEntry[] } | PerformanceEntry[]>("/portfolio/performance")
      .then((res) => {
        const raw = res.data;
        setData(Array.isArray(raw) ? raw : []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <ChartCard title="Portfolio Performance">
      {loading ? (
        <p className="text-text-muted text-base">Loading...</p>
      ) : data.length === 0 ? (
        <p className="text-text-muted text-base">No performance data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#004E59"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
