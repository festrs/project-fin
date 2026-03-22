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
        <p style={{ color: "var(--text-tertiary)", fontSize: "1rem" }}>Loading...</p>
      ) : data.length === 0 ? (
        <p style={{ color: "var(--text-tertiary)", fontSize: "1rem" }}>No performance data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: "rgba(255,255,255,0.35)" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "rgba(255,255,255,0.35)" }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                background: "#1c1c1e",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 8,
                color: "#f5f5f7",
                fontSize: "0.75rem",
              }}
              labelStyle={{ color: "#f5f5f7" }}
              itemStyle={{ color: "#f5f5f7" }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#34c759"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </ChartCard>
  );
}
