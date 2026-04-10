import { useParams, useSearchParams, Link } from "react-router-dom";
import {
  AreaChart,
  Area,
  XAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useAssetDetail } from "../hooks/useAssetDetail";
import { formatMoney, moneyToNumber } from "../utils/money";

type Period = "1W" | "1M" | "3M" | "1Y" | "ALL";

export default function AssetDetail() {
  const { assetClassId, symbol } = useParams<{ assetClassId: string; symbol: string }>();
  const [searchParams] = useSearchParams();
  const country = searchParams.get("country") || "US";
  const type = searchParams.get("type") || "stock";

  const {
    priceHistory,
    holding,
    transactions,
    dividends,
    fundamentals,
    period,
    changePeriod,
    loading,
    error,
  } = useAssetDetail(symbol!, country, assetClassId!, type);

  const chartData = priceHistory.map((p) => ({
    date: p.date,
    price: parseFloat(p.price.amount),
  }));

  const chartGain =
    chartData.length >= 2 ? chartData[chartData.length - 1].price - chartData[0].price : 0;
  const chartColor = chartGain >= 0 ? "#34c759" : "#ff3b30";

  const gainLossNum = moneyToNumber(holding?.gain_loss);
  const currentPrice = holding?.current_price;
  const currency = currentPrice?.currency || holding?.total_cost.currency || "USD";

  const typeBadgeColor = (t: string) => {
    switch (t) {
      case "buy":
        return "#34c759";
      case "sell":
        return "#ff3b30";
      case "dividend":
        return "var(--blue)";
      default:
        return "var(--text-tertiary)";
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <Link
          to={`/portfolio/${assetClassId}`}
          className="inline-flex items-center gap-1 text-text-tertiary hover:opacity-80 transition-colors text-base"
        >
          &larr; Back to Holdings
        </Link>
        <div className="card p-6">
          <div className="animate-pulse space-y-4">
            <div style={{ height: 32, width: 200, borderRadius: 8, background: "var(--surface-hover)" }} />
            <div style={{ height: 200, borderRadius: 8, background: "var(--surface-hover)" }} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <Link
          to={`/portfolio/${assetClassId}`}
          className="inline-flex items-center gap-1 text-text-tertiary hover:opacity-80 transition-colors text-base"
        >
          &larr; Back to Holdings
        </Link>
        <div className="card p-6">
          <p style={{ color: "var(--red)" }}>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back button */}
      <Link
        to={`/portfolio/${assetClassId}`}
        className="inline-flex items-center gap-1 text-text-tertiary hover:opacity-80 transition-colors text-base"
      >
        &larr; Back to Holdings
      </Link>

      {/* Header */}
      <div className="card" style={{ padding: 24 }}>
        <div className="flex justify-between items-start">
          <div>
            <h1
              style={{
                fontSize: 32,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                color: "var(--text-primary)",
                lineHeight: 1,
                marginBottom: 8,
              }}
            >
              {symbol}
            </h1>
            {currentPrice && (
              <p
                style={{
                  fontSize: 24,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                }}
                className="tabular-nums"
              >
                {formatMoney(currentPrice)}
              </p>
            )}
          </div>

          {/* Period selector */}
          <div className="flex gap-2">
            {(["1W", "1M", "3M", "1Y", "ALL"] as Period[]).map((p) => (
              <button
                key={p}
                className={`period-btn${period === p ? " active" : ""}`}
                onClick={() => changePeriod(p)}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        {/* Price chart */}
        {chartData.length > 0 ? (
          <div className="h-48 w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="assetDetailGradient" x1="0" y1="0" x2="0" y2="1">
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
                    `${formatMoney({ amount: String(value), currency })}`,
                    "Price",
                  ]}
                />
                <Area
                  type="monotone"
                  dataKey="price"
                  stroke={chartColor}
                  strokeWidth={2.5}
                  fill="url(#assetDetailGradient)"
                  dot={false}
                  activeDot={{ r: 4, fill: chartColor, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="h-48 w-full mt-4 flex items-center justify-center">
            <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>No price history available</p>
          </div>
        )}
      </div>

      {/* Key stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card" style={{ padding: 16 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 4,
            }}
          >
            Quantity
          </p>
          <p
            style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}
            className="tabular-nums"
          >
            {holding?.quantity != null ? holding.quantity : "--"}
          </p>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 4,
            }}
          >
            Avg Cost
          </p>
          <p
            style={{ fontSize: 20, fontWeight: 700, color: "var(--text-primary)" }}
            className="tabular-nums"
          >
            {holding?.avg_price ? formatMoney(holding.avg_price) : "--"}
          </p>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 4,
            }}
          >
            Total Gain/Loss
          </p>
          <p
            style={{
              fontSize: 20,
              fontWeight: 700,
              color:
                gainLossNum > 0
                  ? "#34c759"
                  : gainLossNum < 0
                  ? "#ff3b30"
                  : "var(--text-primary)",
            }}
            className="tabular-nums"
          >
            {holding?.gain_loss
              ? `${gainLossNum > 0 ? "+" : ""}${formatMoney(holding.gain_loss)}`
              : "--"}
          </p>
        </div>

        <div className="card" style={{ padding: 16 }}>
          <p
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 4,
            }}
          >
            Fundamentals
          </p>
          <p
            style={{
              fontSize: 20,
              fontWeight: 700,
              color: fundamentals
                ? fundamentals.composite_score >= 90
                  ? "var(--green)"
                  : fundamentals.composite_score >= 60
                  ? "var(--orange)"
                  : "var(--red)"
                : "var(--text-primary)",
            }}
            className="tabular-nums"
          >
            {fundamentals ? `${fundamentals.composite_score}%` : "--"}
          </p>
        </div>
      </div>

      {/* Transactions */}
      <div className="card" style={{ padding: 24 }}>
        <h2
          className="text-lg font-semibold tracking-[-0.3px] mb-4"
          style={{ color: "var(--text-primary)" }}
        >
          Transactions
        </h2>
        {transactions.length === 0 ? (
          <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>No transactions found</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-base">
              <thead>
                <tr className="text-text-tertiary uppercase text-base tracking-wide">
                  <th className="text-left px-3 py-2">Date</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-right px-3 py-2">Price</th>
                  <th className="text-right px-3 py-2">Total</th>
                  <th className="text-left px-3 py-2">Notes</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((t) => (
                  <tr key={t.id} className="hover:bg-[var(--row-hover)]">
                    <td className="px-3 py-2">{t.date}</td>
                    <td className="px-3 py-2">
                      <span
                        style={{
                          display: "inline-block",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: 12,
                          fontWeight: 600,
                          textTransform: "uppercase",
                          color: "#fff",
                          background: typeBadgeColor(t.type),
                        }}
                      >
                        {t.type}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {t.quantity != null ? t.quantity : "--"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {t.unit_price ? formatMoney(t.unit_price) : "--"}
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">
                      {formatMoney(t.total_value)}
                    </td>
                    <td className="px-3 py-2 text-text-tertiary truncate max-w-[200px]">
                      {t.notes || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Dividend history */}
      {dividends.length > 0 && (
        <div className="card" style={{ padding: 24 }}>
          <h2
            className="text-lg font-semibold tracking-[-0.3px] mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Dividend History
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-base">
              <thead>
                <tr className="text-text-tertiary uppercase text-base tracking-wide">
                  <th className="text-left px-3 py-2">Ex Date</th>
                  <th className="text-left px-3 py-2">Type</th>
                  <th className="text-right px-3 py-2">Value/Share</th>
                  <th className="text-right px-3 py-2">Qty</th>
                  <th className="text-right px-3 py-2">Total</th>
                  <th className="text-left px-3 py-2">Payment Date</th>
                </tr>
              </thead>
              <tbody>
                {dividends.map((d, idx) => (
                  <tr key={idx} className="hover:bg-[var(--row-hover)]">
                    <td className="px-3 py-2">{d.ex_date}</td>
                    <td className="px-3 py-2 capitalize">{d.dividend_type}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{formatMoney(d.value)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{d.quantity}</td>
                    <td className="px-3 py-2 text-right tabular-nums" style={{ color: "var(--blue)" }}>
                      {formatMoney(d.total)}
                    </td>
                    <td className="px-3 py-2 text-text-tertiary">{d.payment_date || "-"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
