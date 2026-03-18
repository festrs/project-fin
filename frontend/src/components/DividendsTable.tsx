import { useState } from "react";
import { DataTable, type Column } from "./DataTable";
import { TransactionForm } from "./TransactionForm";
import type { Transaction } from "../types";

interface DividendsTableProps {
  dividends: Transaction[];
  loading: boolean;
  onCreateTransaction: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  defaultAssetClassId?: string;
}

type DividendRow = Transaction & Record<string, unknown>;

export function DividendsTable({
  dividends,
  loading,
  onCreateTransaction,
  defaultAssetClassId = "",
}: DividendsTableProps) {
  const [showForm, setShowForm] = useState(false);
  const [formSymbol, setFormSymbol] = useState("");
  const [symbolFilter, setSymbolFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  let filtered = dividends;
  if (symbolFilter) {
    const lower = symbolFilter.toLowerCase();
    filtered = filtered.filter((d) =>
      d.asset_symbol.toLowerCase().includes(lower)
    );
  }
  if (dateFrom) {
    filtered = filtered.filter((d) => d.date >= dateFrom);
  }
  if (dateTo) {
    filtered = filtered.filter((d) => d.date <= dateTo);
  }

  const rows: DividendRow[] = filtered.map((d) => ({ ...d }));

  const columns: Column<DividendRow>[] = [
    {
      key: "asset_symbol",
      header: "Symbol",
      sortable: true,
    },
    {
      key: "date",
      header: "Date",
      sortable: true,
    },
    {
      key: "total_value",
      header: "Amount",
      sortable: true,
      render: (row) => `$${(row.total_value as number).toFixed(2)}`,
    },
    {
      key: "currency",
      header: "Currency",
    },
    {
      key: "tax_amount",
      header: "Tax",
      sortable: true,
      render: (row) => `$${(row.tax_amount as number).toFixed(2)}`,
    },
    {
      key: "notes",
      header: "Notes",
      render: (row) => (row.notes as string | null) || "-",
    },
  ];

  if (loading) {
    return <div>Loading dividends...</div>;
  }

  return (
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px]">Dividends</h2>
        <button
          className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
          onClick={() => setShowForm(!showForm)}
        >
          Add Dividend
        </button>
      </div>

      <div className="flex gap-3 mb-4 items-end flex-wrap">
        <div>
          <label className="block text-base text-text-muted mb-1">Filter by Symbol</label>
          <input
            type="text"
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            placeholder="Symbol..."
          />
        </div>
        <div>
          <label className="block text-base text-text-muted mb-1">From</label>
          <input
            type="date"
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-base text-text-muted mb-1">To</label>
          <input
            type="date"
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
      </div>

      {showForm && (
        <div className="mb-4">
          <div className="mb-2">
            <label className="block text-base text-text-muted mb-1">Symbol</label>
            <input
              type="text"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={formSymbol}
              onChange={(e) => setFormSymbol(e.target.value)}
              placeholder="AAPL"
            />
          </div>
          {formSymbol && (
            <TransactionForm
              symbol={formSymbol}
              assetClassId={defaultAssetClassId}
              type="stock"
              initialType="dividend"
              onSubmit={async (data) => {
                await onCreateTransaction(data);
                setShowForm(false);
                setFormSymbol("");
              }}
              onCancel={() => {
                setShowForm(false);
                setFormSymbol("");
              }}
            />
          )}
        </div>
      )}

      <DataTable
        columns={columns}
        data={rows}
        getRowId={(r) => r.id as string}
      />
    </div>
  );
}
