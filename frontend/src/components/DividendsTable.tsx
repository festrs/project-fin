import { useState } from "react";
import { DataTable, Column } from "./DataTable";
import { TransactionForm } from "./TransactionForm";
import { Transaction } from "../types";

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
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Dividends</h2>
        <button
          className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
          onClick={() => setShowForm(!showForm)}
        >
          Add Dividend
        </button>
      </div>

      <div className="flex gap-3 mb-4 items-end flex-wrap">
        <div>
          <label className="block text-xs text-gray-600 mb-1">Filter by Symbol</label>
          <input
            type="text"
            className="border rounded px-2 py-1 text-sm"
            value={symbolFilter}
            onChange={(e) => setSymbolFilter(e.target.value)}
            placeholder="Symbol..."
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">From</label>
          <input
            type="date"
            className="border rounded px-2 py-1 text-sm"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-600 mb-1">To</label>
          <input
            type="date"
            className="border rounded px-2 py-1 text-sm"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
      </div>

      {showForm && (
        <div className="mb-4">
          <div className="mb-2">
            <label className="block text-xs text-gray-600 mb-1">Symbol</label>
            <input
              type="text"
              className="border rounded px-2 py-1 text-sm"
              value={formSymbol}
              onChange={(e) => setFormSymbol(e.target.value)}
              placeholder="AAPL"
            />
          </div>
          {formSymbol && (
            <TransactionForm
              symbol={formSymbol}
              assetClassId={defaultAssetClassId}
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
