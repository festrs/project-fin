import { useState } from "react";
import { QuarantineBadge } from "./QuarantineBadge";
import { TransactionForm } from "./TransactionForm";
import type { Holding, Transaction, QuarantineStatus, AssetClass } from "../types";

interface HoldingsTableProps {
  holdings: Holding[];
  assetClasses: AssetClass[];
  loading: boolean;
  quarantineStatuses?: QuarantineStatus[];
  transactions: Transaction[];
  onFetchTransactions: (symbol: string) => Promise<void>;
  onCreateTransaction: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onUpdateWeight?: (symbol: string, targetWeight: number) => Promise<unknown>;
  onAddAsset?: (symbol: string, assetClassId: string) => Promise<unknown>;
}

function formatCurrency(value: number, currency?: string): string {
  if (currency === "BRL") return `R$${value.toFixed(2)}`;
  return `$${value.toFixed(2)}`;
}

interface GroupedHoldings {
  classId: string;
  className: string;
  holdings: Holding[];
}

function groupByAssetClass(holdings: Holding[], assetClasses: AssetClass[]): GroupedHoldings[] {
  const classMap = new Map(assetClasses.map((ac) => [ac.id, ac.name]));
  const groups = new Map<string, Holding[]>();

  for (const h of holdings) {
    const list = groups.get(h.asset_class_id) ?? [];
    list.push(h);
    groups.set(h.asset_class_id, list);
  }

  // Sort groups: by class name
  const result: GroupedHoldings[] = [];
  for (const [classId, classHoldings] of groups) {
    result.push({
      classId,
      className: classMap.get(classId) ?? classId,
      holdings: classHoldings,
    });
  }
  result.sort((a, b) => a.className.localeCompare(b.className));
  return result;
}

export function HoldingsTable({
  holdings,
  assetClasses,
  loading,
  quarantineStatuses = [],
  transactions,
  onFetchTransactions,
  onCreateTransaction,
  onUpdateWeight,
  onAddAsset,
}: HoldingsTableProps) {
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [transactionForm, setTransactionForm] = useState<{
    symbol: string;
    assetClassId: string;
    type: "buy" | "sell" | "dividend";
  } | null>(null);
  const [showAddAsset, setShowAddAsset] = useState(false);
  const [newSymbol, setNewSymbol] = useState("");
  const [newAssetClassId, setNewAssetClassId] = useState("");
  const [editingWeight, setEditingWeight] = useState<{ symbol: string; value: string } | null>(null);

  const quarantineMap = new Map(
    quarantineStatuses.map((q) => [q.asset_symbol, q])
  );

  const groups = groupByAssetClass(holdings, assetClasses);

  const toggleGroup = (classId: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(classId)) next.delete(classId);
      else next.add(classId);
      return next;
    });
  };

  const handleRowClick = async (symbol: string) => {
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

  const commitWeightEdit = () => {
    if (editingWeight && onUpdateWeight) {
      const parsed = parseFloat(editingWeight.value);
      if (!isNaN(parsed)) {
        onUpdateWeight(editingWeight.symbol, parsed);
      }
    }
    setEditingWeight(null);
  };

  if (loading) {
    return <div>Loading holdings...</div>;
  }

  return (
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px]">Holdings</h2>
        {onAddAsset && (
          <button
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
            onClick={() => setShowAddAsset(!showAddAsset)}
          >
            Add Asset
          </button>
        )}
      </div>

      {showAddAsset && (
        <form onSubmit={handleAddAsset} className="mb-4 flex gap-2 items-end">
          <div>
            <label className="block text-base text-text-muted mb-1">Symbol</label>
            <input
              type="text"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              placeholder="AAPL"
            />
          </div>
          <div>
            <label className="block text-base text-text-muted mb-1">Asset Class ID</label>
            <input
              type="text"
              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
              value={newAssetClassId}
              onChange={(e) => setNewAssetClassId(e.target.value)}
              placeholder="class-id"
            />
          </div>
          <button
            type="submit"
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
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

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-text-muted uppercase text-base tracking-wide">
              <th className="text-left px-3 py-2">Symbol</th>
              <th className="text-right px-3 py-2">Qty</th>
              <th className="text-right px-3 py-2">Avg Price</th>
              <th className="text-right px-3 py-2">Current Price</th>
              <th className="text-right px-3 py-2">Current Value</th>
              <th className="text-right px-3 py-2">Gain/Loss</th>
              <th className="text-right px-3 py-2">Target %</th>
              <th className="text-right px-3 py-2">Actual %</th>
              <th className="text-center px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => {
              const isCollapsed = collapsedGroups.has(group.classId);
              const groupTotal = group.holdings.reduce(
                (sum, h) => sum + (h.current_value ?? h.total_cost),
                0
              );
              const groupCurrency = group.holdings[0]?.currency ?? "USD";

              return (
                <GroupSection
                  key={group.classId}
                  group={group}
                  isCollapsed={isCollapsed}
                  groupTotal={groupTotal}
                  groupCurrency={groupCurrency}
                  quarantineMap={quarantineMap}
                  expandedRow={expandedRow}
                  transactions={transactions}
                  editingWeight={editingWeight}
                  onToggleGroup={() => toggleGroup(group.classId)}
                  onRowClick={handleRowClick}
                  onBuy={(symbol, classId) =>
                    setTransactionForm({ symbol, assetClassId: classId, type: "buy" })
                  }
                  onSell={(symbol, classId) =>
                    setTransactionForm({ symbol, assetClassId: classId, type: "sell" })
                  }
                  onStartEditWeight={
                    onUpdateWeight
                      ? (symbol, current) =>
                          setEditingWeight({ symbol, value: String(current ?? 0) })
                      : undefined
                  }
                  onWeightChange={(value) =>
                    setEditingWeight((prev) => (prev ? { ...prev, value } : null))
                  }
                  onCommitWeight={commitWeightEdit}
                  onCancelWeight={() => setEditingWeight(null)}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

interface GroupSectionProps {
  group: GroupedHoldings;
  isCollapsed: boolean;
  groupTotal: number;
  groupCurrency: string;
  quarantineMap: Map<string, QuarantineStatus>;
  expandedRow: string | null;
  transactions: Transaction[];
  editingWeight: { symbol: string; value: string } | null;
  onToggleGroup: () => void;
  onRowClick: (symbol: string) => void;
  onBuy: (symbol: string, classId: string) => void;
  onSell: (symbol: string, classId: string) => void;
  onStartEditWeight?: (symbol: string, current: number | undefined) => void;
  onWeightChange: (value: string) => void;
  onCommitWeight: () => void;
  onCancelWeight: () => void;
}

function GroupSection({
  group,
  isCollapsed,
  groupTotal,
  groupCurrency,
  quarantineMap,
  expandedRow,
  transactions,
  editingWeight,
  onToggleGroup,
  onRowClick,
  onBuy,
  onSell,
  onStartEditWeight,
  onWeightChange,
  onCommitWeight,
  onCancelWeight,
}: GroupSectionProps) {
  return (
    <>
      {/* Group header row */}
      <tr
        className="bg-[var(--glass-primary-soft)] cursor-pointer hover:bg-[rgba(79,70,229,0.08)]"
        onClick={onToggleGroup}
      >
        <td colSpan={4} className="px-3 py-2 font-semibold text-primary">
          <span className="mr-2 text-xs">{isCollapsed ? "▶" : "▼"}</span>
          {group.className}
          <span className="ml-2 text-xs font-normal text-text-muted">
            ({group.holdings.length} {group.holdings.length === 1 ? "asset" : "assets"})
          </span>
        </td>
        <td className="px-3 py-2 text-right font-semibold text-primary">
          {formatCurrency(groupTotal, groupCurrency)}
        </td>
        <td colSpan={4} />
      </tr>

      {/* Holdings rows */}
      {!isCollapsed &&
        group.holdings.map((h) => {
          const q = quarantineMap.get(h.symbol);
          const isExpanded = expandedRow === h.symbol;
          const isEditingThis = editingWeight?.symbol === h.symbol;

          return (
            <HoldingRows
              key={h.symbol}
              holding={h}
              quarantine={q}
              isExpanded={isExpanded}
              transactions={transactions}
              classId={group.classId}
              isEditingWeight={isEditingThis}
              editWeightValue={isEditingThis ? editingWeight!.value : undefined}
              onRowClick={() => onRowClick(h.symbol)}
              onBuy={() => onBuy(h.symbol, group.classId)}
              onSell={() => onSell(h.symbol, group.classId)}
              onStartEditWeight={
                onStartEditWeight
                  ? () => onStartEditWeight(h.symbol, h.target_weight)
                  : undefined
              }
              onWeightChange={onWeightChange}
              onCommitWeight={onCommitWeight}
              onCancelWeight={onCancelWeight}
            />
          );
        })}
    </>
  );
}

interface HoldingRowsProps {
  holding: Holding;
  quarantine?: QuarantineStatus;
  isExpanded: boolean;
  transactions: Transaction[];
  classId: string;
  isEditingWeight: boolean;
  editWeightValue?: string;
  onRowClick: () => void;
  onBuy: () => void;
  onSell: () => void;
  onStartEditWeight?: () => void;
  onWeightChange: (value: string) => void;
  onCommitWeight: () => void;
  onCancelWeight: () => void;
}

function HoldingRows({
  holding: h,
  quarantine: q,
  isExpanded,
  transactions,
  isEditingWeight,
  editWeightValue,
  onRowClick,
  onBuy,
  onSell,
  onStartEditWeight,
  onWeightChange,
  onCommitWeight,
  onCancelWeight,
}: HoldingRowsProps) {
  const cur = h.currency as string;
  const sym = cur === "BRL" ? "R$" : "$";

  return (
    <>
      <tr className="even:bg-[var(--glass-row-alt)] hover:bg-[var(--glass-hover)] cursor-pointer rounded-lg" onClick={onRowClick}>
        <td className="px-3 py-2 pl-8">
          <span className="flex items-center gap-2">
            <span className="font-medium">{h.symbol}</span>
            {q && (
              <QuarantineBadge
                isQuarantined={q.is_quarantined}
                endsAt={q.quarantine_ends_at}
              />
            )}
          </span>
        </td>
        <td className="px-3 py-2 text-right">{h.quantity}</td>
        <td className="px-3 py-2 text-right">{formatCurrency(h.avg_price, cur)}</td>
        <td className="px-3 py-2 text-right">
          {h.current_price != null ? formatCurrency(h.current_price, cur) : "-"}
        </td>
        <td className="px-3 py-2 text-right">
          {h.current_value != null ? formatCurrency(h.current_value, cur) : "-"}
        </td>
        <td className="px-3 py-2 text-right">
          {h.gain_loss != null ? (
            <span
              className={
                h.gain_loss > 0
                  ? "text-positive"
                  : h.gain_loss < 0
                  ? "text-negative"
                  : ""
              }
            >
              {h.gain_loss === 0
                ? `${sym}0.00`
                : h.gain_loss > 0
                ? `+${sym}${h.gain_loss.toFixed(2)}`
                : `-${sym}${Math.abs(h.gain_loss).toFixed(2)}`}
            </span>
          ) : (
            "-"
          )}
        </td>
        <td
          className="px-3 py-2 text-right"
          onDoubleClick={(e) => {
            e.stopPropagation();
            onStartEditWeight?.();
          }}
        >
          {isEditingWeight ? (
            <input
              type="text"
              className="border border-primary rounded px-1 py-0.5 text-sm w-16 text-right"
              value={editWeightValue}
              onChange={(e) => onWeightChange(e.target.value)}
              onBlur={onCommitWeight}
              onKeyDown={(e) => {
                if (e.key === "Enter") onCommitWeight();
                if (e.key === "Escape") onCancelWeight();
              }}
              onClick={(e) => e.stopPropagation()}
              autoFocus
            />
          ) : (
            <span>{h.target_weight != null ? `${h.target_weight}%` : "-"}</span>
          )}
        </td>
        <td className="px-3 py-2 text-right">
          {h.actual_weight != null ? `${h.actual_weight.toFixed(1)}%` : "-"}
        </td>
        <td className="px-3 py-2 text-center">
          <span className="flex gap-1 justify-center">
            <button
              className="text-positive hover:opacity-80 text-base px-2 font-medium"
              onClick={(e) => {
                e.stopPropagation();
                onBuy();
              }}
            >
              Buy
            </button>
            <button
              className="text-negative hover:opacity-80 text-base px-2 font-medium"
              onClick={(e) => {
                e.stopPropagation();
                onSell();
              }}
            >
              Sell
            </button>
          </span>
        </td>
      </tr>

      {/* Expanded transaction history */}
      {isExpanded && (
        <tr>
          <td colSpan={9} className="px-4 py-3 bg-[var(--glass-row-alt)] rounded-lg">
            <h4 className="font-semibold text-base text-text-primary mb-2">Transaction History</h4>
            {transactions.length === 0 ? (
              <p className="text-text-muted text-base">No transactions found</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-text-muted">
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
                      <td className="py-1 px-2 text-right">
                        {t.currency === "BRL" ? "R$" : "$"}
                        {t.unit_price.toFixed(2)}
                      </td>
                      <td className="py-1 px-2 text-right">
                        {t.currency === "BRL" ? "R$" : "$"}
                        {t.total_value.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
