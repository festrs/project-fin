import { useState } from "react";
import type { Transaction } from "../types";

type TransactionType = "buy" | "sell" | "dividend";

interface TransactionFormProps {
  symbol: string;
  assetClassId: string;
  initialType?: TransactionType;
  onSubmit: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onCancel: () => void;
}

export function TransactionForm({
  symbol,
  assetClassId,
  initialType = "buy",
  onSubmit,
  onCancel,
}: TransactionFormProps) {
  const [type, setType] = useState<TransactionType>(initialType);
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [totalValue, setTotalValue] = useState("");
  const [currency, setCurrency] = useState<"BRL" | "USD">("BRL");
  const [taxAmount, setTaxAmount] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const isDividend = type === "dividend";

  const computedTotal =
    !isDividend && quantity && unitPrice
      ? (parseFloat(quantity) * parseFloat(unitPrice)).toFixed(2)
      : totalValue;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await onSubmit({
        asset_class_id: assetClassId,
        asset_symbol: symbol,
        type,
        quantity: isDividend ? 0 : parseFloat(quantity) || 0,
        unit_price: isDividend ? 0 : parseFloat(unitPrice) || 0,
        total_value: isDividend ? parseFloat(totalValue) || 0 : parseFloat(computedTotal) || 0,
        currency,
        tax_amount: parseFloat(taxAmount) || 0,
        date,
        notes: notes || null,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3 p-4 bg-gray-50 rounded border">
      <h3 className="font-semibold text-sm">
        New Transaction - {symbol}
      </h3>

      <div className="flex gap-2">
        <label className="text-sm">
          Type:
          <select
            className="ml-1 border rounded px-2 py-1 text-sm"
            value={type}
            onChange={(e) => setType(e.target.value as TransactionType)}
          >
            <option value="buy">Buy</option>
            <option value="sell">Sell</option>
            <option value="dividend">Dividend</option>
          </select>
        </label>
      </div>

      {!isDividend && (
        <div className="flex gap-3">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Quantity</label>
            <input
              type="number"
              step="any"
              className="border rounded px-2 py-1 text-sm w-28"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Unit Price</label>
            <input
              type="number"
              step="any"
              className="border rounded px-2 py-1 text-sm w-28"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Total</label>
            <input
              type="text"
              className="border rounded px-2 py-1 text-sm w-28 bg-gray-100"
              value={computedTotal}
              readOnly
            />
          </div>
        </div>
      )}

      {isDividend && (
        <div>
          <label className="block text-xs text-gray-600 mb-1">Total Value</label>
          <input
            type="number"
            step="any"
            className="border rounded px-2 py-1 text-sm w-28"
            value={totalValue}
            onChange={(e) => setTotalValue(e.target.value)}
            required
          />
        </div>
      )}

      <div className="flex gap-3">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Currency</label>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={currency}
            onChange={(e) => setCurrency(e.target.value as "BRL" | "USD")}
          >
            <option value="BRL">BRL</option>
            <option value="USD">USD</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Tax Amount</label>
          <input
            type="number"
            step="any"
            className="border rounded px-2 py-1 text-sm w-28"
            value={taxAmount}
            onChange={(e) => setTaxAmount(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">Date</label>
          <input
            type="date"
            className="border rounded px-2 py-1 text-sm"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </div>
      </div>

      <div>
        <label className="block text-xs text-gray-600 mb-1">Notes</label>
        <input
          type="text"
          className="border rounded px-2 py-1 text-sm w-full"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional notes"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="bg-blue-600 text-white px-3 py-1 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Saving..." : "Save"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="text-gray-500 px-3 py-1 rounded text-sm hover:text-gray-700"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
