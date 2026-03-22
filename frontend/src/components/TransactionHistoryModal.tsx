import { useEffect, useState } from "react";
import api from "../services/api";
import { formatMoney } from "../utils/money";
import type { Transaction } from "../types";

interface TransactionHistoryModalProps {
  className: string;
  assetClassId: string;
  symbols: string[];
  onClose: () => void;
}

export function TransactionHistoryModal({
  className,
  symbols,
  onClose,
}: TransactionHistoryModalProps) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all(
      symbols.map((sym) =>
        api.get<Transaction[]>("/transactions", { params: { symbol: sym } }).then((r) => r.data)
      )
    )
      .then((results) => {
        const all = results
          .flat()
          .sort((a, b) => b.date.localeCompare(a.date));
        setTransactions(all);
      })
      .finally(() => setLoading(false));
  }, [symbols]);

  const formatDate = (iso: string) => {
    const [year, month, day] = iso.split("-");
    return `${day}/${month}/${year}`;
  };

  // Group by symbol
  const bySymbol = new Map<string, Transaction[]>();
  for (const t of transactions) {
    const list = bySymbol.get(t.asset_symbol) ?? [];
    list.push(t);
    bySymbol.set(t.asset_symbol, list);
  }

  const typeColor = (type: string) => {
    if (type === "buy") return "var(--green)";
    if (type === "sell") return "var(--red)";
    return "var(--blue)";
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0, 0, 0, 0.7)" }}
      onClick={onClose}
    >
      <div
        className="card-elevated w-full max-w-lg max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-heading">
            {className} — Transactions
          </h3>
          <button
            onClick={onClose}
            className="text-text-tertiary hover:opacity-80 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {loading ? (
          <p className="text-text-tertiary text-base">Loading...</p>
        ) : transactions.length === 0 ? (
          <p className="text-text-tertiary text-base">No transactions found.</p>
        ) : (
          <div className="space-y-4">
            {[...bySymbol.entries()].map(([symbol, records]) => (
              <div key={symbol}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-base font-medium text-blue">
                    {symbol}{" "}
                    <span className="text-text-tertiary text-sm">
                      ({records.length} transaction{records.length !== 1 ? "s" : ""})
                    </span>
                  </span>
                </div>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-label">
                      <th className="text-left py-1 px-1">Date</th>
                      <th className="text-left py-1 px-1">Type</th>
                      <th className="text-right py-1 px-1">Qty</th>
                      <th className="text-right py-1 px-1">Price</th>
                      <th className="text-right py-1 px-1">Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.map((t) => (
                      <tr key={t.id} className="table-row">
                        <td className="py-1 px-1 text-text-tertiary">{formatDate(t.date)}</td>
                        <td className="py-1 px-1 capitalize" style={{ color: typeColor(t.type) }}>
                          {t.type}
                        </td>
                        <td className="py-1 px-1 text-right tabular-nums">
                          {t.quantity != null ? t.quantity : "—"}
                        </td>
                        <td className="py-1 px-1 text-right tabular-nums">
                          {t.unit_price ? formatMoney(t.unit_price) : "—"}
                        </td>
                        <td className="py-1 px-1 text-right tabular-nums" style={{ color: "var(--text-primary)" }}>
                          {formatMoney(t.total_value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
