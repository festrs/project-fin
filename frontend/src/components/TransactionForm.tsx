import { useState } from "react";
import type { Transaction, AssetClassType } from "../types";

type TransactionType = "buy" | "sell" | "dividend";

interface TransactionFormProps {
  symbol: string;
  assetClassId: string;
  type: AssetClassType;
  initialType?: TransactionType;
  onSubmit: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onCancel: () => void;
}

export function TransactionForm({
  symbol,
  assetClassId,
  type: assetClassType,
  initialType = "buy",
  onSubmit,
  onCancel,
}: TransactionFormProps) {
  const [type, setType] = useState<TransactionType>(initialType);
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [totalValue, setTotalValue] = useState("");
  const [currency, setCurrency] = useState("BRL");
  const [taxAmount, setTaxAmount] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isFixedIncome = assetClassType === "fixed_income";
  const isDividend = type === "dividend";
  const hideQuantityFields = isDividend || isFixedIncome;

  const computedTotal =
    !hideQuantityFields && quantity && unitPrice
      ? (parseFloat(quantity) * parseFloat(unitPrice)).toFixed(2)
      : totalValue;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const finalTotal = hideQuantityFields ? parseFloat(totalValue) || 0 : parseFloat(computedTotal) || 0;
      await onSubmit({
        asset_class_id: assetClassId,
        asset_symbol: symbol,
        type,
        quantity: hideQuantityFields ? null : parseFloat(quantity) || 0,
        unit_price: hideQuantityFields ? null : { amount: String(parseFloat(unitPrice) || 0), currency },
        total_value: { amount: String(finalTotal), currency },
        tax_amount: isFixedIncome ? null : { amount: String(parseFloat(taxAmount) || 0), currency },
        date,
        notes: notes || null,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="card space-y-4 p-6">
      <h3 className="font-semibold text-base text-on-surface">
        New Transaction - {symbol}
      </h3>

      <div className="flex gap-2">
        <label className="text-base text-on-surface-variant">
          Type:
          <select
            className="ml-1 input-field"
            value={type}
            onChange={(e) => setType(e.target.value as TransactionType)}
          >
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
            {!isFixedIncome && <option value="dividend">Dividend</option>}
          </select>
        </label>
      </div>

      {!hideQuantityFields && (
        <div className="flex gap-3">
          <div>
            <label className="block text-base text-on-surface-variant mb-1">Quantity</label>
            <input
              type="number"
              step="any"
              className="input-field w-28"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-base text-on-surface-variant mb-1">Unit Price</label>
            <input
              type="number"
              step="any"
              className="input-field w-28"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-base text-on-surface-variant mb-1">Total</label>
            <input
              type="text"
              className="bg-[rgba(0,0,0,0.03)] border border-[var(--glass-border)] rounded-sm px-3.5 py-2.5 text-base w-28 text-on-surface-variant"
              value={computedTotal}
              readOnly
            />
          </div>
        </div>
      )}

      {hideQuantityFields && (
        <div>
          <label className="block text-base text-on-surface-variant mb-1">Total Value</label>
          <input
            type="number"
            step="any"
            className="input-field w-28"
            value={totalValue}
            onChange={(e) => setTotalValue(e.target.value)}
            required
          />
        </div>
      )}

      <div className="flex gap-3">
        <div>
          <label className="block text-base text-on-surface-variant mb-1">Currency</label>
          <select
            className="input-field"
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
          >
            {["BRL", "USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD"].map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        {!isFixedIncome && (
          <div>
            <label className="block text-base text-on-surface-variant mb-1">Tax Amount</label>
            <input
              type="number"
              step="any"
              className="input-field w-28"
              value={taxAmount}
              onChange={(e) => setTaxAmount(e.target.value)}
            />
          </div>
        )}
        <div>
          <label className="block text-base text-on-surface-variant mb-1">Date</label>
          <input
            type="date"
            className="input-field"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-base text-on-surface-variant mb-1">Notes</label>
        <input
          type="text"
          className="input-field w-full"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional notes"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="btn-primary disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="btn-ghost"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
