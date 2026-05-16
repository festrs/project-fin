import { useState } from "react";
import BigChart from "./BigChart";
import { usePortfolioHistory } from "../hooks/usePortfolioHistory";

type Period = "1D" | "1W" | "1M" | "1Y" | "ALL";

interface PortfolioHeroCardProps {
  grandTotalBRL: number;
  loading: boolean;
}

function fmtBRL(n: number): string {
  return "R$\u00A0" + Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export default function PortfolioHeroCard({ grandTotalBRL, loading }: PortfolioHeroCardProps) {
  const [selectedPeriod, setSelectedPeriod] = useState<Period>("1M");
  const { history, latestSnapshot, loading: historyLoading } = usePortfolioHistory(selectedPeriod);

  const formattedValue = grandTotalBRL.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const chartData = history.map((s) => parseFloat(s.total_value_brl));

  const periodGain = chartData.length >= 2 ? chartData[chartData.length - 1] - chartData[0] : 0;
  const periodPct = chartData.length >= 2 && chartData[0] !== 0 ? (periodGain / chartData[0]) * 100 : 0;

  function renderChart() {
    if (selectedPeriod === "1D") {
      if (!latestSnapshot) {
        return (
          <div style={{ height: 240, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <p style={{ color: "var(--fg-3)", fontSize: 14 }}>No snapshot yet</p>
          </div>
        );
      }

      const snapshotValue = parseFloat(latestSnapshot.total_value_brl);
      const delta = grandTotalBRL - snapshotValue;
      const deltaPct = snapshotValue !== 0 ? (delta / snapshotValue) * 100 : 0;
      const isPositive = delta >= 0;
      const color = isPositive ? "var(--up)" : "var(--down)";

      return (
        <div style={{ height: 240, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 4 }}>
          <span className="num" style={{ fontSize: 32, fontWeight: 700, color }}>
            {isPositive ? "+" : ""}R${" "}
            {Math.abs(delta).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
          <span className="num" style={{ fontSize: 14, fontWeight: 500, color }}>
            {isPositive ? "+" : ""}{deltaPct.toFixed(2)}%
          </span>
          <span style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 4 }}>Today&apos;s change</span>
        </div>
      );
    }

    if (historyLoading) {
      return (
        <div style={{ height: 240 }}>
          <div className="animate-pulse" style={{ height: "100%", width: "100%", borderRadius: 8, background: "var(--bg-3)" }} />
        </div>
      );
    }

    if (chartData.length === 0) {
      return (
        <div style={{ height: 240, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <p style={{ color: "var(--fg-3)", fontSize: 14 }}>No history data yet</p>
        </div>
      );
    }

    return (
      <BigChart
        data={chartData}
        height={240}
        formatValue={fmtBRL}
        formatLabel={(i, total) => {
          const snap = history[i];
          return snap ? new Date(snap.date).toLocaleDateString("pt-BR", { day: "2-digit", month: "short" }) : `Day -${total - 1 - i}`;
        }}
      />
    );
  }

  return (
    <section
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--line)",
        borderRadius: "var(--radius)",
        padding: "28px 28px 20px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
        <div>
          <div className="section-title">Total balance</div>
          {loading ? (
            <div className="animate-pulse" style={{ height: 44, width: 256, borderRadius: 8, background: "var(--bg-3)", marginTop: 4 }} />
          ) : (
            <div className="num" style={{
              fontFamily: "var(--font-display)",
              fontSize: 44,
              fontWeight: 600,
              letterSpacing: "-0.03em",
              marginTop: 4,
            }}>
              R$ {formattedValue}
            </div>
          )}
          {!loading && selectedPeriod !== "1D" && chartData.length >= 2 && (
            <div style={{ display: "flex", gap: 14, marginTop: 6, alignItems: "center" }}>
              <span className="num" style={{ color: periodGain >= 0 ? "var(--up)" : "var(--down)", fontWeight: 500, fontSize: 14 }}>
                {periodGain >= 0 ? "+" : ""}R$ {Math.abs(periodGain).toLocaleString("pt-BR", { maximumFractionDigits: 0 })}
                {" · "}
                {periodGain >= 0 ? "+" : ""}{periodPct.toFixed(2)}%
              </span>
              <span style={{ color: "var(--fg-3)", fontSize: 13 }}>{selectedPeriod}</span>
            </div>
          )}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
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
      <div style={{ marginTop: 20 }}>
        {renderChart()}
      </div>
    </section>
  );
}
