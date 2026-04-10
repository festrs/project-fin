import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { usePortfolioHistory } from "../hooks/usePortfolioHistory";

type Period = "1D" | "1W" | "1M" | "1Y" | "ALL";

interface PortfolioHeroCardProps {
  grandTotalBRL: number;
  loading: boolean;
}

export default function PortfolioHeroCard({ grandTotalBRL, loading }: PortfolioHeroCardProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<Period>("1M");
  const { history, latestSnapshot, loading: historyLoading } = usePortfolioHistory(selectedPeriod);

  const formattedValue = grandTotalBRL.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const chartData = history.map((s) => ({
    date: s.date,
    value: parseFloat(s.total_value_brl),
  }));

  const periodGain =
    chartData.length >= 2 ? chartData[chartData.length - 1].value - chartData[0].value : 0;
  const chartColor = periodGain >= 0 ? "#34c759" : "#ff3b30";

  function renderChart() {
    if (selectedPeriod === "1D") {
      if (!latestSnapshot) {
        return (
          <div className="h-48 w-full mt-4 flex items-center justify-center">
            <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>No snapshot yet</p>
          </div>
        );
      }

      const snapshotValue = parseFloat(latestSnapshot.total_value_brl);
      const delta = grandTotalBRL - snapshotValue;
      const deltaPct = snapshotValue !== 0 ? (delta / snapshotValue) * 100 : 0;
      const isPositive = delta >= 0;
      const color = isPositive ? "#34c759" : "#ff3b30";

      return (
        <div className="h-48 w-full mt-4 flex flex-col items-center justify-center gap-1">
          <span style={{ fontSize: 32, fontWeight: 700, color }} className="tabular-nums">
            {isPositive ? "+" : ""}
            R${" "}
            {Math.abs(delta).toLocaleString("pt-BR", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            })}
          </span>
          <span style={{ fontSize: 14, fontWeight: 500, color }} className="tabular-nums">
            {isPositive ? "+" : ""}
            {deltaPct.toFixed(2)}%
          </span>
          <span style={{ fontSize: 12, color: "var(--text-tertiary)", marginTop: 4 }}>
            Today&apos;s change
          </span>
        </div>
      );
    }

    if (historyLoading) {
      return (
        <div className="h-48 w-full mt-4">
          <div
            className="animate-pulse"
            style={{
              height: "100%",
              width: "100%",
              borderRadius: 8,
              background: "var(--surface-hover)",
            }}
          />
        </div>
      );
    }

    if (chartData.length === 0) {
      return (
        <div className="h-48 w-full mt-4 flex items-center justify-center">
          <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>No history data yet</p>
        </div>
      );
    }

    const gradientId = "heroGradient";

    return (
      <div className="h-48 w-full mt-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={chartColor} stopOpacity={0.2} />
                <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="date" hide />
            <Tooltip
              contentStyle={{
                background: "var(--surface-elevated)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                fontSize: 13,
                color: "var(--text-primary)",
              }}
              labelFormatter={(label) =>
                new Date(String(label)).toLocaleDateString("pt-BR", {
                  day: "2-digit",
                  month: "short",
                  year: "numeric",
                })
              }
              formatter={(value) => [
                `R$ ${Number(value).toLocaleString("pt-BR", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}`,
                "Value",
              ]}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={chartColor}
              strokeWidth={2.5}
              fill={`url(#${gradientId})`}
              dot={false}
              activeDot={{ r: 4, fill: chartColor, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div
      className="relative overflow-hidden"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "24px",
      }}
    >
      <div className="flex justify-between items-start mb-6">
        <div>
          <p
            className="text-label"
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 4,
            }}
          >
            Portfolio Value
          </p>
          {loading ? (
            <div
              className="animate-pulse"
              style={{ height: 56, width: 256, borderRadius: 8, background: "var(--surface-hover)" }}
            />
          ) : (
            <h3
              style={{
                fontSize: 56,
                fontWeight: 700,
                letterSpacing: "-0.03em",
                color: "var(--text-primary)",
                lineHeight: 1,
              }}
              className="tabular-nums"
            >
              R$ {formattedValue}
            </h3>
          )}
        </div>
        <div className="flex gap-2">
          {(["1D", "1W", "1M", "1Y", "ALL"] as Period[]).map((period) => (
            <button
              key={period}
              className={`period-btn${selectedPeriod === period ? " active" : ""}`}
              onClick={() => setSelectedPeriod(period)}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {renderChart()}
    </div>
  );
}
