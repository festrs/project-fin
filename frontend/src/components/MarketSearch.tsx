import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useMarketData, type Quote } from "../hooks/useMarketData";

function getDisplayName(quote: Quote): string {
  if ("name" in quote) return quote.name;
  if ("coin_id" in quote) return (quote as { coin_id: string }).coin_id;
  return "";
}

function getMarketCap(quote: Quote): string {
  const cap = quote.market_cap;
  if (cap >= 1e12) return `${(cap / 1e12).toFixed(2)}T`;
  if (cap >= 1e9) return `${(cap / 1e9).toFixed(2)}B`;
  if (cap >= 1e6) return `${(cap / 1e6).toFixed(2)}M`;
  return cap.toLocaleString();
}

export function MarketSearch() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState<"stock" | "crypto">("stock");
  const { quote, history, loading, error, searchStock, searchCrypto } =
    useMarketData();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    if (type === "stock") {
      searchStock(query.trim().toUpperCase());
    } else {
      searchCrypto(query.trim().toLowerCase());
    }
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-4 items-end">
        <div className="flex-1">
          <label htmlFor="search" className="block text-base font-medium text-text-secondary mb-1">
            Search
          </label>
          <input
            id="search"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={type === "stock" ? "e.g. AAPL" : "e.g. bitcoin"}
            className="w-full bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
          />
        </div>
        <div className="flex gap-3 items-center pb-1">
          <label className="flex items-center gap-1 text-base">
            <input
              type="radio"
              name="marketType"
              value="stock"
              checked={type === "stock"}
              onChange={() => setType("stock")}
            />
            Stock
          </label>
          <label className="flex items-center gap-1 text-base">
            <input
              type="radio"
              name="marketType"
              value="crypto"
              checked={type === "crypto"}
              onChange={() => setType("crypto")}
            />
            Crypto
          </label>
        </div>
        <button
          type="submit"
          disabled={loading}
          className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="text-negative text-base bg-[var(--glass-negative-soft)] rounded-[10px] px-4 py-3">{error}</p>}

      {quote && (
        <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-base text-text-muted">Name</p>
              <p className="font-semibold">{getDisplayName(quote)}</p>
            </div>
            <div>
              <p className="text-base text-text-muted">Price</p>
              <p className="font-semibold">
                {quote.currency} {quote.price.toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-base text-text-muted">Currency</p>
              <p className="font-semibold">{quote.currency}</p>
            </div>
            <div>
              <p className="text-base text-text-muted">Market Cap</p>
              <p className="font-semibold">{getMarketCap(quote)}</p>
            </div>
          </div>

          {history.length > 0 && (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={history}>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} domain={["auto", "auto"]} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#4f46e5"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      )}
    </div>
  );
}
