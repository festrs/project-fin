import { useParams, useNavigate } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
  LineChart,
  Line,
  ReferenceLine,
  Cell,
} from "recharts";
import { useFundamentalsDetail } from "../hooks/useFundamentals";
import type { FundamentalsScore } from "../types";

const RATING_COLORS = {
  green: "var(--green)",
  yellow: "var(--orange)",
  red: "var(--red)",
};

// Hex values for Recharts (which doesn't support CSS variables in fill/stroke)
const CHART_COLORS = {
  green: "#34c759",
  yellow: "#ff9f0a",
  red: "#ff3b30",
};

type Rating = "green" | "yellow" | "red";

function RatingDot({ rating }: { rating: Rating }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        backgroundColor: RATING_COLORS[rating],
        marginRight: 8,
        flexShrink: 0,
      }}
    />
  );
}

function compositeColor(score: number): string {
  if (score >= 90) return RATING_COLORS.green;
  if (score >= 60) return RATING_COLORS.yellow;
  return RATING_COLORS.red;
}

function ScoreBreakdownCard({ detail }: { detail: FundamentalsScore }) {
  const criteria: { label: string; rating: Rating }[] = [
    {
      label: `IPO Age: ${detail.ipo_years != null ? `${detail.ipo_years} yrs` : "N/A"}`,
      rating: detail.ipo_rating,
    },
    {
      label: `EPS Growth: ${detail.eps_growth_pct != null ? `${detail.eps_growth_pct.toFixed(1)}%` : "N/A"}`,
      rating: detail.eps_rating,
    },
    {
      label: `Net Debt/EBITDA: ${detail.current_net_debt_ebitda != null ? detail.current_net_debt_ebitda.toFixed(2) : "N/A"} (High debt ${detail.high_debt_years_pct != null ? `${detail.high_debt_years_pct.toFixed(0)}%` : "N/A"} of years)`,
      rating: detail.debt_rating,
    },
    {
      label: `Profitability: ${detail.profitable_years_pct != null ? `${detail.profitable_years_pct.toFixed(0)}% profitable years` : "N/A"}`,
      rating: detail.profit_rating,
    },
  ];

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-heading text-blue">Score Breakdown</h2>
        <span
          className="text-2xl font-bold"
          style={{ color: compositeColor(detail.composite_score) }}
        >
          {detail.composite_score}%
        </span>
      </div>
      <ul className="space-y-3">
        {criteria.map((c) => (
          <li key={c.label} className="flex items-center">
            <RatingDot rating={c.rating} />
            <span style={{ color: "var(--text-secondary)" }} className="text-sm">{c.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Fundamentals() {
  const { symbol } = useParams<{ symbol: string }>();
  const navigate = useNavigate();
  const { detail, loading, error, refresh } = useFundamentalsDetail(
    symbol ?? ""
  );

  if (loading) {
    return (
      <div className="text-blue text-center mt-20">
        Loading fundamentals...
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center mt-20">
        <p className="text-red mb-4">{error}</p>
        <button onClick={refresh} className="btn-ghost px-4 py-2 text-sm">
          Retry
        </button>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="text-text-tertiary text-center mt-20">No data available.</div>
    );
  }

  const rawData = detail.raw_data ?? [];

  // EPS chart data with color per bar
  const epsData = rawData.map((d, i) => ({
    year: String(d.year),
    eps: d.eps,
    color:
      i === 0
        ? "#8884d8"
        : d.eps > rawData[i - 1].eps
          ? CHART_COLORS.green
          : CHART_COLORS.red,
  }));

  // Net Debt/EBITDA chart data
  const debtData = rawData.map((d) => ({
    year: String(d.year),
    value: d.net_debt_ebitda,
  }));

  // Net Income chart data
  const incomeData = rawData.map((d) => ({
    year: String(d.year),
    net_income: d.net_income,
    color: d.net_income > 0 ? CHART_COLORS.green : CHART_COLORS.red,
  }));

  const axisStyle = { stroke: "rgba(255,255,255,0.35)", fontSize: 12 };
  const gridStyle = {
    strokeDasharray: "3 3",
    stroke: "rgba(255,255,255,0.08)",
  };

  const tooltipStyle = {
    backgroundColor: "#1c1c1e",
    border: "1px solid rgba(255,255,255,0.08)",
    color: "#f5f5f7",
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="btn-ghost px-3 py-1.5 text-sm"
          >
            ← Back
          </button>
          <h1 className="text-blue text-2xl font-bold">
            {symbol} Fundamentals
          </h1>
        </div>
        <button
          onClick={refresh}
          className="btn-ghost px-4 py-2 text-sm font-medium"
        >
          Refresh
        </button>
      </div>

      {/* Score Breakdown */}
      <ScoreBreakdownCard detail={detail} />

      {/* EPS History */}
      {epsData.length > 0 && (
        <div className="card">
          <h2 className="text-heading text-blue mb-4">
            EPS History
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={epsData}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="year" tick={axisStyle} />
              <YAxis tick={axisStyle} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="eps" isAnimationActive={false}>
                {epsData.map((entry, index) => (
                  <Cell key={`eps-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Net Debt / EBITDA */}
      {debtData.length > 0 && (
        <div className="card">
          <h2 className="text-heading text-blue mb-4">
            Net Debt / EBITDA
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={debtData}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="year" tick={axisStyle} />
              <YAxis tick={axisStyle} />
              <Tooltip contentStyle={tooltipStyle} />
              <ReferenceLine
                y={3}
                stroke="#ff3b30"
                strokeDasharray="4 4"
                label={{
                  value: "Threshold (3x)",
                  fill: "#ff3b30",
                  fontSize: 12,
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#8884d8"
                dot={{ r: 4 }}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Net Income (Profitability) */}
      {incomeData.length > 0 && (
        <div className="card">
          <h2 className="text-heading text-blue mb-4">
            Net Income
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={incomeData}>
              <CartesianGrid {...gridStyle} />
              <XAxis dataKey="year" tick={axisStyle} />
              <YAxis tick={axisStyle} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="net_income" isAnimationActive={false}>
                {incomeData.map((entry, index) => (
                  <Cell key={`income-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Updated at */}
      {detail.updated_at && (
        <p className="text-text-tertiary text-xs text-right">
          Updated at: {new Date(detail.updated_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
