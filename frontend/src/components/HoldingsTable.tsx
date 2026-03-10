import { useState } from "react";
import { DataTable, Column } from "./DataTable";
import { QuarantineBadge } from "./QuarantineBadge";
import { TransactionForm } from "./TransactionForm";
import { Holding, Transaction, QuarantineStatus } from "../types";

interface HoldingsTableProps {
  holdings: Holding[];
  loading: boolean;
  quarantineStatuses?: QuarantineStatus[];
  transactions: Transaction[];
  onFetchTransactions: (symbol: string) => Promise<void>;
  onCreateTransaction: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onUpdateWeight?: (symbol: string, targetWeight: number) => Promise<unknown>;
  onAddAsset?: (symbol: string, assetClassId: string) => Promise<unknown>;
}

type HoldingRow = Holding & Record<string, unknown>;

export function HoldingsTable({
  holdings,
  loading,
  quarantineStatuses = [],
  transactions,
  onFetchTransactions,
  onCreateTransaction,
  onUpdateWeight,
  onAddAsset,
}: HoldingsTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [transactionForm, setTransactionForm] = useState<{
    symbol: string;
    assetClassId: string;
    type: "buy" | "sell" | "dividend";
  } | null>(null);
  const [showAddAsset, setShowAddAsset] = useState(false);
  const [newSymbol, setNewSymbol] = useState("");
  const [newAssetClassId, setNewAssetClassId] = useState("");

  const quarantineMap = new Map(
    quarantineStatuses.map((q) => [q.asset_symbol, q])
  );

  const rows: HoldingRow[] = holdings.map((h) => ({ ...h }));

  const columns: Column<HoldingRow>[] = [
    {
      key: "symbol",
      header: "Symbol",
      sortable: true,
      render: (row) => {
        const q = quarantineMap.get(row.symbol as string);
        return (
          <span className="flex items-center gap-2">
            <span className="font-medium">{row.symbol as string}</span>
            {q && (
              <QuarantineBadge
                isQuarantined={q.is_quarantined}
                endsAt={q.quarantine_ends_at}
              />
            )}
          </span>
        );
      },
    },
    {
      key: "quantity",
      header: "Qty",
      sortable: true,
      render: (row) => String(row.quantity),
    },
    {
      key: "avg_price",
      header: "Avg Price",
      sortable: true,
      render: (row) => `$${(row.avg_price as number).toFixed(2)}`,
    },
    {
      key: "current_price",
      header: "Current Price",
      sortable: true,
      render: (row) =>
        row.current_price != null ? `$${(row.current_price as number).toFixed(2)}` : "-",
    },
    {
      key: "gain_loss",
      header: "Gain/Loss",
      sortable: true,
      render: (row) => {
        if (row.gain_loss == null) return "-";
        const val = row.gain_loss as number;
        const color = val > 0 ? "text-green-600" : val < 0 ? "text-red-600" : "";
        const formatted = val > 0 ? `+$${val.toFixed(2)}` : `-$${Math.abs(val).toFixed(2)}`;
        return <span className={color}>{val === 0 ? "$0.00" : formatted}</span>;
      },
    },
    {
      key: "target_weight",
      header: "Target Weight",
      sortable: true,
      editable: !!onUpdateWeight,
      onEdit: (row, value) => {
        const parsed = parseFloat(value);
        if (!isNaN(parsed) && onUpdateWeight) {
          onUpdateWeight(row.symbol as string, parsed);
        }
      },
      render: (row) =>
        row.target_weight != null ? `${row.target_weight}%` : "-",
    },
    {
      key: "actual_weight",
      header: "Actual Weight",
      sortable: true,
      render: (row) =>
        row.actual_weight != null ? `${(row.actual_weight as number).toFixed(1)}%` : "-",
    },
    {
      key: "_actions",
      header: "",
      render: (row) => (
        <span className="flex gap-1">
          <button
            className="text-green-600 hover:text-green-800 text-xs px-1"
            onClick={(e) => {
              e.stopPropagation();
              setTransactionForm({
                symbol: row.symbol as string,
                assetClassId: row.asset_class_id as string,
                type: "buy",
              });
            }}
          >
            Buy
          </button>
          <button
            className="text-red-600 hover:text-red-800 text-xs px-1"
            onClick={(e) => {
              e.stopPropagation();
              setTransactionForm({
                symbol: row.symbol as string,
                assetClassId: row.asset_class_id as string,
                type: "sell",
              });
            }}
          >
            Sell
          </button>
        </span>
      ),
    },
  ];

  const handleRowClick = async (row: HoldingRow) => {
    const symbol = row.symbol as string;
    if (expandedRow === symbol) {
      setExpandedRow(null);
    } else {
      setExpandedRow(symbol);
      await onFetchTransactions(symbol);
    }
  };

  const handleAddAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (onAddAsset && newSymbol.trim() && newAssetClassId.trim()) {
      await onAddAsset(newSymbol.trim(), newAssetClassId.trim());
      setNewSymbol("");
      setNewAssetClassId("");
      setShowAddAsset(false);
    }
  };

  if (loading) {
    return <div>Loading holdings...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Holdings</h2>
        {onAddAsset && (
          <button
            className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700"
            onClick={() => setShowAddAsset(!showAddAsset)}
          >
            Add Asset
          </button>
        )}
      </div>

      {showAddAsset && (
        <form onSubmit={handleAddAsset} className="mb-4 flex gap-2 items-end">
          <div>
            <label className="block text-xs text-gray-600 mb-1">Symbol</label>
            <input
              type="text"
              className="border rounded px-2 py-1 text-sm"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="AAPL"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-600 mb-1">Asset Class ID</label>
            <input
              type="text"
              className="border rounded px-2 py-1 text-sm"
              value={newAssetClassId}
              onChange={(e) => setNewAssetClassId(e.target.value)}
              placeholder="class-id"
            />
          </div>
          <button
            type="submit"
            className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
          >
            Add
          </button>
        </form>
      )}

      {transactionForm && (
        <div className="mb-4">
          <TransactionForm
            symbol={transactionForm.symbol}
            assetClassId={transactionForm.assetClassId}
            initialType={transactionForm.type}
            onSubmit={async (data) => {
              await onCreateTransaction(data);
              setTransactionForm(null);
            }}
            onCancel={() => setTransactionForm(null)}
          />
        </div>
      )}

      <DataTable
        columns={columns}
        data={rows}
        getRowId={(r) => r.symbol as string}
        onRowClick={handleRowClick}
        expandedRow={expandedRow}
        renderExpanded={() => (
          <div>
            <h4 className="font-semibold text-sm mb-2">Transaction History</h4>
            {transactions.length === 0 ? (
              <p className="text-gray-500 text-sm">No transactions found</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-500">
                    <th className="text-left py-1 px-2">Date</th>
                    <th className="text-left py-1 px-2">Type</th>
                    <th className="text-right py-1 px-2">Qty</th>
                    <th className="text-right py-1 px-2">Price</th>
                    <th className="text-right py-1 px-2">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    <tr key={t.id} className="border-t">
                      <td className="py-1 px-2">{t.date}</td>
                      <td className="py-1 px-2 capitalize">{t.type}</td>
                      <td className="py-1 px-2 text-right">{t.quantity}</td>
                      <td className="py-1 px-2 text-right">${t.unit_price.toFixed(2)}</td>
                      <td className="py-1 px-2 text-right">${t.total_value.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      />
    </div>
  );
}
