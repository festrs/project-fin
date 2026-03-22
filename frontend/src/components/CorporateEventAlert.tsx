import type { StockSplit } from "../types";
import { SPLIT_EVENT_TYPE } from "../types";

interface CorporateEventAlertProps {
  splits: StockSplit[];
  actionLoading: Record<string, boolean>;
  onApply: (splitId: string) => void;
  onDismiss: (splitId: string) => void;
}

export default function CorporateEventAlert({ splits, actionLoading, onApply, onDismiss }: CorporateEventAlertProps) {
  if (splits.length === 0) return null;

  return (
    <div className="space-y-3">
      {splits.map((split) => {
        const isLoading = actionLoading[split.id] ?? false;
        const label = split.event_type === SPLIT_EVENT_TYPE.BONIFICACAO ? "Bonificação" : "Stock Split";

        return (
          <div
            key={split.id}
            className={`rounded-xl p-4 flex items-center justify-between border-l-4 border-primary ${
              isLoading ? "opacity-60" : ""
            }`}
            style={{ background: "var(--color-surface-high)" }}
          >
            <div className="flex items-center gap-4">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-primary"
                style={{ background: "var(--primary-soft)" }}
              >
                <span className="material-symbols-outlined">event_note</span>
              </div>
              <div>
                <h4 className="text-sm font-bold text-on-surface">
                  Pending Corporate Event: {split.symbol} {label}
                </h4>
                <p className="text-xs text-on-surface-variant font-body">
                  Ratio {split.from_factor}:{split.to_factor} — {split.current_quantity} shares → {split.new_quantity.toFixed(0)} shares
                </p>
              </div>
            </div>
            <div className="flex gap-3 shrink-0">
              <button
                onClick={() => onApply(split.id)}
                disabled={isLoading}
                className="btn-primary px-4 py-1.5 text-xs"
              >
                {isLoading ? "Applying..." : "Apply"}
              </button>
              <button
                onClick={() => onDismiss(split.id)}
                disabled={isLoading}
                className="px-4 py-1.5 text-xs font-bold text-on-surface-variant hover:text-on-surface transition-colors"
              >
                {isLoading ? "..." : "Dismiss"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
