import { useState, useEffect, useRef } from "react";
import type { AssetClass, Transaction } from "../types";
import { isFixedIncomeClass } from "../utils/assetClass";
import api from "../services/api";

interface SearchResult {
  symbol: string;
  name: string;
  type: string;
}

interface AddAssetFormProps {
  assetClasses: AssetClass[];
  onSubmit: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onCancel: () => void;
}

const CURRENCIES = ["BRL", "USD", "EUR", "GBP", "CHF", "JPY", "CAD", "AUD"];

export function AddAssetForm({ assetClasses, onSubmit, onCancel }: AddAssetFormProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [selectedName, setSelectedName] = useState("");
  const [useCustomSymbol, setUseCustomSymbol] = useState(false);
  const [assetClassId, setAssetClassId] = useState(assetClasses[0]?.id ?? "");
  const [quantity, setQuantity] = useState("");
  const [unitPrice, setUnitPrice] = useState("");
  const [currency, setCurrency] = useState("BRL");
  const [taxAmount, setTaxAmount] = useState("");
  const [date, setDate] = useState(new Date().toISOString().split("T")[0]);
  const [totalValue, setTotalValue] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const selectedClass = assetClasses.find((ac) => ac.id === assetClassId);
  const isFixedIncome = isFixedIncomeClass(selectedClass?.name ?? "");
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (query.length < 2 || selectedSymbol) {
      setResults([]);
      setShowDropdown(false);
      return;
    }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        const res = await api.get<SearchResult[]>("/stocks/search", { params: { q: query } });
        setResults(res.data);
        setShowDropdown(res.data.length > 0);
      } catch {
        setResults([]);
        setShowDropdown(false);
      } finally {
        setSearching(false);
      }
    }, 300);

    return () => clearTimeout(debounceRef.current);
  }, [query, selectedSymbol]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (result: SearchResult) => {
    setSelectedSymbol(result.symbol);
    setSelectedName(result.name);
    setQuery(result.symbol);
    setShowDropdown(false);
    setCurrency(result.symbol.endsWith(".SA") ? "BRL" : "USD");
  };

  const handleClearSymbol = () => {
    setSelectedSymbol("");
    setSelectedName("");
    setQuery("");
    setResults([]);
    setUseCustomSymbol(false);
  };

  const handleConfirmCustom = () => {
    if (query.trim()) {
      setSelectedSymbol(query.trim());
      setShowDropdown(false);
    }
  };

  const computedTotal = quantity && unitPrice
    ? (parseFloat(quantity) * parseFloat(unitPrice)).toFixed(2)
    : "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedSymbol || !assetClassId) return;
    setSubmitting(true);
    try {
      if (isFixedIncome) {
        await onSubmit({
          asset_class_id: assetClassId,
          asset_symbol: selectedSymbol,
          type: "buy",
          quantity: null,
          unit_price: null,
          total_value: parseFloat(totalValue) || 0,
          currency: currency as "BRL" | "USD",
          tax_amount: null,
          date,
          notes: notes || null,
        });
      } else {
        await onSubmit({
          asset_class_id: assetClassId,
          asset_symbol: selectedSymbol,
          type: "buy",
          quantity: parseFloat(quantity) || 0,
          unit_price: parseFloat(unitPrice) || 0,
          total_value: parseFloat(computedTotal) || 0,
          currency: currency as "BRL" | "USD",
          tax_amount: parseFloat(taxAmount) || 0,
          date,
          notes: notes || null,
        });
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 p-6 bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] mb-4">
      <h3 className="font-semibold text-base text-text-primary">Add New Asset</h3>

      <div className="flex gap-3 flex-wrap items-end">
        {/* Symbol search */}
        <div className="relative" ref={dropdownRef}>
          <label className="block text-base text-text-muted mb-1">Symbol / Name</label>
          {selectedSymbol ? (
            <div className="flex items-center gap-2">
              <span className="bg-[var(--glass-primary-soft)] text-primary font-semibold px-3 py-2 rounded-[10px] text-base">
                {selectedSymbol}
                {selectedName && <span className="text-text-muted font-normal ml-1.5">— {selectedName}</span>}
              </span>
              <button
                type="button"
                onClick={handleClearSymbol}
                className="text-text-muted hover:text-negative text-base px-1"
              >
                ×
              </button>
            </div>
          ) : (
            <>
              <div className="flex gap-2 items-center">
                <input
                  type="text"
                  className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary w-64"
                  value={query}
                  onChange={(e) => {
                    const val = useCustomSymbol ? e.target.value : e.target.value.toUpperCase();
                    setQuery(val);
                    setSelectedSymbol("");
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && useCustomSymbol && query.trim()) {
                      e.preventDefault();
                      handleConfirmCustom();
                    }
                  }}
                  placeholder={useCustomSymbol ? "CDB Banco X 120% CDI..." : "Search BBSA3, AAPL..."}
                  autoFocus
                />
                {useCustomSymbol && query.trim() && (
                  <button
                    type="button"
                    onClick={handleConfirmCustom}
                    className="bg-primary text-white px-3 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover whitespace-nowrap"
                  >
                    Confirm
                  </button>
                )}
              </div>
              {searching && (
                <span className="absolute right-3 top-9 text-text-muted text-base">...</span>
              )}
              {!useCustomSymbol && showDropdown && (
                <ul className="absolute z-10 mt-1 w-80 max-h-60 overflow-y-auto bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[10px] shadow-lg">
                  {results.map((r) => (
                    <li
                      key={r.symbol}
                      className="px-3 py-2 hover:bg-[var(--glass-hover)] cursor-pointer text-base flex justify-between"
                      onClick={() => handleSelect(r)}
                    >
                      <span className="font-medium text-primary">{r.symbol}</span>
                      <span className="text-text-muted truncate ml-2">{r.name}</span>
                    </li>
                  ))}
                </ul>
              )}
              <button
                type="button"
                onClick={() => {
                  setUseCustomSymbol(!useCustomSymbol);
                  setShowDropdown(false);
                  setResults([]);
                  setQuery("");
                }}
                className="text-base text-primary hover:text-primary-hover mt-1"
              >
                {useCustomSymbol ? "Search market instead" : "Use custom name (fixed income, etc.)"}
              </button>
            </>
          )}
        </div>

        {/* Asset class */}
        <div>
          <label className="block text-base text-text-muted mb-1">Asset Class</label>
          <select
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            value={assetClassId}
            onChange={(e) => setAssetClassId(e.target.value)}
            required
          >
            {assetClasses.map((ac) => (
              <option key={ac.id} value={ac.id}>{ac.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Buy transaction fields */}
      {isFixedIncome ? (
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="block text-base text-text-muted mb-1">Total Value</label>
            <input
              type="number"
              step="any"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary w-36"
              value={totalValue}
              onChange={(e) => setTotalValue(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Currency</label>
            <select
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Date</label>
            <input
              type="date"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </div>
        </div>
      ) : (
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <label className="block text-base text-text-muted mb-1">Quantity</label>
            <input
              type="number"
              step="any"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary w-28"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Unit Price</label>
            <input
              type="number"
              step="any"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary w-28"
              value={unitPrice}
              onChange={(e) => setUnitPrice(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Total</label>
            <input
              type="text"
              className="bg-[rgba(0,0,0,0.03)] border border-[var(--glass-border)] rounded-[10px] px-3.5 py-2.5 text-base w-28 text-text-muted"
              value={computedTotal}
              readOnly
            />
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Currency</label>
            <select
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
            >
              {CURRENCIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Tax</label>
            <input
              type="number"
              step="any"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary w-24"
              value={taxAmount}
              onChange={(e) => setTaxAmount(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Date</label>
            <input
              type="date"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </div>
        </div>
      )}

      <div>
        <label className="block text-base text-text-muted mb-1">Notes</label>
        <input
          type="text"
          className="w-full bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Optional notes"
        />
      </div>

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting || !selectedSymbol}
          className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
        >
          {submitting ? "Adding..." : "Add Asset"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="bg-[rgba(0,0,0,0.03)] border border-[var(--glass-border)] text-text-secondary px-4 py-2 rounded-[10px] text-base font-medium hover:bg-[rgba(0,0,0,0.06)]"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
