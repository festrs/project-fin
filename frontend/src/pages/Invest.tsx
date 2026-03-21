import { useState } from "react";
import { useInvest } from "../hooks/useInvest";

export default function Invest() {
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("BRL");
  const [count, setCount] = useState(3);
  const { plan, loading, error, calculate } = useInvest();

  const handleCalculate = () => {
    if (!amount || parseFloat(amount) <= 0) return;
    calculate(amount, currency, count);
  };

  const formatMoney = (value: { amount: string; currency: string }) => {
    const num = parseFloat(value.amount);
    if (value.currency === "BRL") {
      return `R$ ${num.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const formatQuantity = (qty: number) => {
    if (qty >= 1 && Number.isInteger(qty)) return qty.toString();
    return qty.toFixed(8).replace(/0+$/, "").replace(/\.$/, "");
  };

  return (
    <div className="space-y-4">
      <h1 className="text-[32px] font-bold text-text-primary tracking-[-0.5px]">Where to Invest</h1>

      {/* Input bar */}
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <div className="flex items-end gap-4 flex-wrap">
          <div>
            <label htmlFor="amount" className="block text-base font-medium text-text-secondary mb-1">
              Amount
            </label>
            <input
              id="amount"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCalculate()}
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary w-40 focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            />
          </div>
          <div>
            <label htmlFor="currency" className="block text-base font-medium text-text-secondary mb-1">
              Currency
            </label>
            <select
              id="currency"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            >
              <option value="BRL">BRL</option>
              <option value="USD">USD</option>
            </select>
          </div>
          <div>
            <label htmlFor="count" className="block text-base font-medium text-text-secondary mb-1">
              # Recommendations
            </label>
            <input
              id="count"
              type="number"
              min="1"
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value, 10) || 1)}
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary w-24 focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            />
          </div>
          <button
            onClick={handleCalculate}
            disabled={loading || !amount}
            className="bg-primary text-white px-6 py-2.5 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {loading ? "Calculating..." : "Calculate"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-negative/10 border border-negative/30 rounded-[14px] p-4">
          <p className="text-negative text-base">{error}</p>
        </div>
      )}

      {/* Results */}
      {!plan && !loading && !error && (
        <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
          <p className="text-text-muted text-base">Enter an amount and click Calculate to get your investment plan.</p>
        </div>
      )}

      {loading && (
        <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
          <p className="text-text-muted text-base">Calculating investment plan...</p>
        </div>
      )}

      {plan && !loading && (
        <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
          <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-4">Investment Plan</h2>

          {plan.recommendations.length === 0 ? (
            <p className="text-text-muted text-base">
              {plan.empty_reason === "no_holdings"
                ? "Add holdings to your portfolio first."
                : plan.empty_reason === "all_quarantined"
                ? "No recommendations available — all top candidates are in quarantine."
                : plan.empty_reason === "amount_too_small"
                ? "Amount too low to purchase any recommended assets."
                : "No recommendations available."}
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-base">
                <thead>
                  <tr className="text-text-muted text-left border-b border-[var(--glass-border)]">
                    <th className="py-2 px-2">Asset</th>
                    <th className="py-2 px-2">Class</th>
                    <th className="py-2 px-2 text-right">Target</th>
                    <th className="py-2 px-2 text-right">Actual</th>
                    <th className="py-2 px-2 text-right">Gap</th>
                    <th className="py-2 px-2 text-right">Price</th>
                    <th className="py-2 px-2 text-right">Qty</th>
                    <th className="py-2 px-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.recommendations.map((rec) => (
                    <tr key={rec.symbol} className="border-b border-[var(--glass-border)] last:border-0 even:bg-[var(--glass-row-alt)]">
                      <td className="py-2.5 px-2 font-semibold text-text-primary">{rec.symbol}</td>
                      <td className="py-2.5 px-2 text-text-muted">{rec.class_name}</td>
                      <td className="py-2.5 px-2 text-right">{rec.effective_target.toFixed(1)}%</td>
                      <td className="py-2.5 px-2 text-right">{rec.actual_weight.toFixed(1)}%</td>
                      <td className="py-2.5 px-2 text-right text-positive">+{rec.diff.toFixed(1)}%</td>
                      <td className="py-2.5 px-2 text-right">{formatMoney(rec.price)}</td>
                      <td className="py-2.5 px-2 text-right font-semibold">{formatQuantity(rec.quantity)}</td>
                      <td className="py-2.5 px-2 text-right font-semibold">{formatMoney(rec.invest_amount)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="border-t-2 border-[var(--glass-border)] font-bold">
                    <td colSpan={7} className="py-3 px-2">Total</td>
                    <td className="py-3 px-2 text-right">{formatMoney(plan.total_invested)}</td>
                  </tr>
                  {parseFloat(plan.remainder.amount) > 0 && (
                    <tr className="text-text-muted">
                      <td colSpan={7} className="py-1 px-2 text-sm">Uninvested remainder</td>
                      <td className="py-1 px-2 text-right text-sm">{formatMoney(plan.remainder)}</td>
                    </tr>
                  )}
                </tfoot>
              </table>
            </div>
          )}

          {plan.exchange_rate && (
            <p className="text-text-muted text-sm mt-3">
              Exchange rate ({plan.exchange_rate_pair}): {plan.exchange_rate.toFixed(2)}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
