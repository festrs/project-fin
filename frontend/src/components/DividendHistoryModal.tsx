import { useEffect, useState } from "react";
import api from "../services/api";
import type { DividendHistoryItem } from "../types";

interface DividendHistoryModalProps {
  className: string;
  assetClassId: string;
  currency: string;
  onClose: () => void;
}

export function DividendHistoryModal({
  className,
  assetClassId,
  currency,
  onClose,
}: DividendHistoryModalProps) {
  const [items, setItems] = useState<DividendHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<DividendHistoryItem[]>("/dividends/history", {
        params: { asset_class_id: assetClassId },
      })
      .then((res) => setItems(res.data))
      .finally(() => setLoading(false));
  }, [assetClassId]);

  const formatValue = (value: number) => {
    if (currency === "BRL") {
      return `R$${value.toLocaleString("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}`;
    }
    return `$${value.toLocaleString("en-US", { minimumFractionDigits: 4, maximumFractionDigits: 4 })}`;
  };

  const formatDate = (iso: string) => {
    const [year, month, day] = iso.split("-");
    return `${day}/${month}/${year}`;
  };

  // Group by symbol
  const bySymbol = new Map<string, DividendHistoryItem[]>();
  for (const item of items) {
    const list = bySymbol.get(item.symbol) ?? [];
    list.push(item);
    bySymbol.set(item.symbol, list);
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">
            {className} — Dividends {new Date().getFullYear()}
          </h3>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {loading ? (
          <p className="text-text-muted text-base">Loading...</p>
        ) : items.length === 0 ? (
          <p className="text-text-muted text-base">No dividend records found for this year.</p>
        ) : (
          <div className="space-y-4">
            {[...bySymbol.entries()].map(([symbol, records]) => {
              const total = records.reduce((sum, r) => sum + r.value, 0);
              return (
                <div key={symbol}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-base font-medium text-primary">{symbol}</span>
                    <span className="text-base font-semibold text-text-primary">
                      {formatValue(total)}
                    </span>
                  </div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-text-muted text-xs uppercase tracking-wide">
                        <th className="text-left py-1 px-1">Type</th>
                        <th className="text-right py-1 px-1">Value</th>
                        <th className="text-right py-1 px-1">Ex Date</th>
                        <th className="text-right py-1 px-1">Payment</th>
                      </tr>
                    </thead>
                    <tbody>
                      {records.map((r, i) => (
                        <tr key={i} className="even:bg-[var(--glass-row-alt)]">
                          <td className="py-1 px-1 text-text-secondary">{r.dividend_type}</td>
                          <td className="py-1 px-1 text-right">{formatValue(r.value)}</td>
                          <td className="py-1 px-1 text-right text-text-muted">{formatDate(r.ex_date)}</td>
                          <td className="py-1 px-1 text-right text-text-muted">
                            {r.payment_date ? formatDate(r.payment_date) : "-"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
