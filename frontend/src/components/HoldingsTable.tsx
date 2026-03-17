import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { QuarantineBadge } from "./QuarantineBadge";
import { TransactionForm } from "./TransactionForm";
import { isFixedIncomeClass } from "../utils/assetClass";
import { AddAssetForm } from "./AddAssetForm";
import type { Holding, Transaction, QuarantineStatus, AssetClass, FundamentalsScore } from "../types";

interface HoldingsTableProps {
  holdings: Holding[];
  assetClasses: AssetClass[];
  loading: boolean;
  quarantineStatuses?: QuarantineStatus[];
  transactions: Transaction[];
  dividendsBySymbol?: Map<string, { income: number; currency: string }>;
  fundamentalsScores?: FundamentalsScore[];
  onRefreshAllScores?: () => Promise<void>;
  onFetchTransactions: (symbol: string) => Promise<void>;
  onCreateTransaction: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onUpdateTransaction?: (id: string, data: Partial<Transaction>) => Promise<unknown>;
  onDeleteTransaction?: (id: string) => Promise<unknown>;
  onDeleteHolding?: (symbol: string) => Promise<unknown>;
  onChangeAssetClass?: (symbol: string, assetClassId: string) => Promise<unknown>;
  onUpdateWeight?: (symbol: string, targetWeight: number) => Promise<unknown>;
  showAddAsset?: boolean;
}

const CURRENCY_SYMBOLS: Record<string, string> = {
  BRL: "R$",
  USD: "$",
  EUR: "\u20AC",
  GBP: "\u00A3",
  CHF: "CHF ",
  JPY: "\u00A5",
  CAD: "CA$",
  AUD: "A$",
};

function formatCurrency(value: number, currency?: string): string {
  const sym = CURRENCY_SYMBOLS[currency ?? "USD"] ?? `${currency ?? ""} `;
  return `${sym}${value.toFixed(2)}`;
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
  dividendsBySymbol = new Map(),
  fundamentalsScores,
  onRefreshAllScores,
  onFetchTransactions,
  onCreateTransaction,
  onUpdateTransaction,
  onDeleteTransaction,
  onDeleteHolding,
  onChangeAssetClass,
  onUpdateWeight,
  showAddAsset: enableAddAsset,
}: HoldingsTableProps) {
  const navigate = useNavigate();
  const scoreMap = new Map((fundamentalsScores ?? []).map((s) => [s.symbol, s]));
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [transactionForm, setTransactionForm] = useState<{
    symbol: string;
    assetClassId: string;
    type: "buy" | "sell" | "dividend";
  } | null>(null);
  const [showAddAsset, setShowAddAsset] = useState(false);
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
        {enableAddAsset && (
          <button
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover"
            onClick={() => setShowAddAsset(!showAddAsset)}
          >
            Add Asset
          </button>
        )}
      </div>

      {showAddAsset && (
        <AddAssetForm
          assetClasses={assetClasses}
          onSubmit={async (data) => {
            await onCreateTransaction(data);
            setShowAddAsset(false);
          }}
          onCancel={() => setShowAddAsset(false)}
        />
      )}

      {transactionForm && (
        <div className="mb-4">
          <TransactionForm
            symbol={transactionForm.symbol}
            assetClassId={transactionForm.assetClassId}
            isFixedIncome={isFixedIncomeClass(
              assetClasses.find((ac) => ac.id === transactionForm.assetClassId)?.name ?? ""
            )}
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
        <table className="w-full text-base">
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
              <th className="text-right px-3 py-2">Div ({new Date().getFullYear()})</th>
              <th className="text-right px-3 py-2">
                <span className="flex items-center justify-end gap-1">
                  Score
                  {onRefreshAllScores && (
                    <button
                      className="text-[10px] text-text-muted hover:text-primary ml-1"
                      title="Fetch scores for all stocks"
                      onClick={onRefreshAllScores}
                    >
                      ↻
                    </button>
                  )}
                </span>
              </th>
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
                  dividendsBySymbol={dividendsBySymbol}
                  scoreMap={scoreMap}
                  onNavigateScore={(symbol) => navigate(`/fundamentals/${symbol}`)}
                  onToggleGroup={() => toggleGroup(group.classId)}
                  onRowClick={handleRowClick}
                  assetClasses={assetClasses}
                  onUpdateTransaction={onUpdateTransaction}
                  onDeleteTransaction={onDeleteTransaction}
                  onDeleteHolding={onDeleteHolding}
                  onChangeAssetClass={onChangeAssetClass}
                  onFetchTransactions={onFetchTransactions}
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
  dividendsBySymbol: Map<string, { income: number; currency: string }>;
  scoreMap: Map<string, FundamentalsScore>;
  assetClasses: AssetClass[];
  onUpdateTransaction?: (id: string, data: Partial<Transaction>) => Promise<unknown>;
  onDeleteTransaction?: (id: string) => Promise<unknown>;
  onDeleteHolding?: (symbol: string) => Promise<unknown>;
  onChangeAssetClass?: (symbol: string, assetClassId: string) => Promise<unknown>;
  onFetchTransactions: (symbol: string) => Promise<void>;
  onNavigateScore: (symbol: string) => void;
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
  dividendsBySymbol,
  scoreMap,
  assetClasses,
  onUpdateTransaction,
  onDeleteTransaction,
  onDeleteHolding,
  onChangeAssetClass,
  onFetchTransactions,
  onNavigateScore,
  onToggleGroup,
  onRowClick,
  onBuy,
  onSell,
  onStartEditWeight,
  onWeightChange,
  onCommitWeight,
  onCancelWeight,
}: GroupSectionProps) {
  const groupDivTotal = group.holdings.reduce((sum, h) => {
    const div = dividendsBySymbol.get(h.symbol);
    return sum + (div?.income ?? 0);
  }, 0);
  const groupDivCurrency = group.holdings[0]?.currency ?? "USD";

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
        <td colSpan={3} />
        <td className="px-3 py-2 text-right font-semibold text-text-muted">
          {groupDivTotal > 0 ? formatCurrency(groupDivTotal, groupDivCurrency) : ""}
        </td>
        <td />
        <td />
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
              dividendData={dividendsBySymbol.get(h.symbol)}
              score={scoreMap.get(h.symbol)}
              assetClasses={assetClasses}
              onUpdateTransaction={onUpdateTransaction}
              onDeleteTransaction={onDeleteTransaction}
              onDeleteHolding={onDeleteHolding}
              onChangeAssetClass={onChangeAssetClass}
              onFetchTransactions={onFetchTransactions}
              onNavigateScore={() => onNavigateScore(h.symbol)}
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
  dividendData?: { income: number; currency: string };
  score?: FundamentalsScore;
  assetClasses: AssetClass[];
  onUpdateTransaction?: (id: string, data: Partial<Transaction>) => Promise<unknown>;
  onDeleteTransaction?: (id: string) => Promise<unknown>;
  onDeleteHolding?: (symbol: string) => Promise<unknown>;
  onChangeAssetClass?: (symbol: string, assetClassId: string) => Promise<unknown>;
  onFetchTransactions: (symbol: string) => Promise<void>;
  onNavigateScore: () => void;
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
  classId,
  isEditingWeight,
  editWeightValue,
  dividendData,
  score,
  assetClasses,
  onUpdateTransaction,
  onDeleteTransaction,
  onDeleteHolding,
  onChangeAssetClass,
  onFetchTransactions,
  onNavigateScore,
  onRowClick,
  onBuy,
  onSell,
  onStartEditWeight,
  onWeightChange,
  onCommitWeight,
  onCancelWeight,
}: HoldingRowsProps) {
  const [editingTx, setEditingTx] = useState<string | null>(null);
  const [editTxData, setEditTxData] = useState<{
    quantity: string;
    unit_price: string;
    total_value: string;
    tax_amount: string;
    date: string;
    notes: string;
  }>({ quantity: "", unit_price: "", total_value: "", date: "", notes: "", tax_amount: "" });
  const [showHoldingMenu, setShowHoldingMenu] = useState(false);
  const [changingAssetClass, setChangingAssetClass] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const cur = h.currency as string;
  const sym = CURRENCY_SYMBOLS[cur] ?? `${cur} `;
  const scoreColor = (v: number) =>
    v >= 90
      ? "var(--color-positive)"
      : v >= 60
      ? "var(--color-warning)"
      : "var(--color-negative)";

  const startEditTx = (t: Transaction) => {
    setEditingTx(t.id);
    setEditTxData({
      quantity: t.quantity != null ? String(t.quantity) : "",
      unit_price: t.unit_price != null ? String(t.unit_price) : "",
      total_value: String(t.total_value),
      tax_amount: t.tax_amount != null ? String(t.tax_amount) : "",
      date: t.date,
      notes: t.notes ?? "",
    });
  };

  const saveEditTx = async (t: Transaction) => {
    if (!onUpdateTransaction) return;
    const isValueBased = t.quantity == null;
    const qty = isValueBased ? null : (parseFloat(editTxData.quantity) || 0);
    const price = isValueBased ? null : (parseFloat(editTxData.unit_price) || 0);
    const total = isValueBased || t.type === "dividend"
      ? parseFloat(editTxData.total_value) || 0
      : (qty ?? 0) * (price ?? 0);
    await onUpdateTransaction(t.id, {
      quantity: qty,
      unit_price: price,
      total_value: total,
      tax_amount: isValueBased ? null : (parseFloat(editTxData.tax_amount) || 0),
      date: editTxData.date,
      notes: editTxData.notes || null,
    });
    setEditingTx(null);
    await onFetchTransactions(h.symbol);
  };

  const handleDeleteTx = async (id: string) => {
    if (!onDeleteTransaction) return;
    await onDeleteTransaction(id);
    await onFetchTransactions(h.symbol);
  };

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
        <td className="px-3 py-2 text-right">{h.quantity != null ? h.quantity : "—"}</td>
        <td className="px-3 py-2 text-right">{h.avg_price != null ? formatCurrency(h.avg_price, cur) : "—"}</td>
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
              className="border border-[var(--glass-border-input)] rounded-[10px] px-2 py-1 text-base w-16 text-right focus:border-primary focus:ring-2 focus:ring-[var(--glass-primary-ring)] outline-none"
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
        <td className="px-3 py-2 text-right text-text-muted">
          {dividendData && dividendData.income > 0
            ? formatCurrency(dividendData.income, dividendData.currency)
            : "-"}
        </td>
        <td className="px-3 py-2 text-right">
          {score ? (
            <span
              style={{ color: scoreColor(score.composite_score), cursor: "pointer", fontWeight: 600 }}
              onClick={(e) => { e.stopPropagation(); onNavigateScore(); }}
              title={`IPO: ${score.ipo_rating} | EPS: ${score.eps_rating} | Debt: ${score.debt_rating} | Profit: ${score.profit_rating}`}
            >
              {score.composite_score}%
            </span>
          ) : (
            <span className="text-text-muted">—</span>
          )}
        </td>
        <td className="px-3 py-2 text-center">
          <span className="flex gap-1 justify-center items-center relative">
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
            {(onDeleteHolding || onChangeAssetClass) && (
              <div className="relative">
                <button
                  className="text-text-muted hover:text-text-primary text-base px-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowHoldingMenu(!showHoldingMenu);
                    setConfirmDelete(false);
                    setChangingAssetClass(false);
                  }}
                  title="More actions"
                >
                  ···
                </button>
                {showHoldingMenu && (
                  <div
                    className="absolute right-0 top-8 z-20 bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[10px] shadow-lg py-1 min-w-[180px]"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {onChangeAssetClass && !changingAssetClass && (
                      <button
                        className="w-full text-left px-3 py-2 text-base text-text-primary hover:bg-[var(--glass-hover)]"
                        onClick={() => setChangingAssetClass(true)}
                      >
                        Change Asset Class
                      </button>
                    )}
                    {changingAssetClass && (
                      <div className="px-3 py-2">
                        <label className="block text-xs text-text-muted mb-1">Move to:</label>
                        <select
                          className="w-full bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[8px] px-2 py-1 text-base"
                          defaultValue={classId}
                          onChange={async (e) => {
                            await onChangeAssetClass!(h.symbol, e.target.value);
                            setShowHoldingMenu(false);
                            setChangingAssetClass(false);
                          }}
                        >
                          {assetClasses.map((ac) => (
                            <option key={ac.id} value={ac.id}>{ac.name}</option>
                          ))}
                        </select>
                      </div>
                    )}
                    {onDeleteHolding && !confirmDelete && (
                      <button
                        className="w-full text-left px-3 py-2 text-base text-negative hover:bg-[var(--glass-hover)]"
                        onClick={() => setConfirmDelete(true)}
                      >
                        Delete Holding
                      </button>
                    )}
                    {confirmDelete && (
                      <div className="px-3 py-2 space-y-1">
                        <p className="text-xs text-negative">Delete all transactions for {h.symbol}?</p>
                        <div className="flex gap-2">
                          <button
                            className="bg-negative text-white px-3 py-1 rounded-[8px] text-xs font-semibold"
                            onClick={async () => {
                              await onDeleteHolding!(h.symbol);
                              setShowHoldingMenu(false);
                            }}
                          >
                            Confirm
                          </button>
                          <button
                            className="text-text-muted text-xs"
                            onClick={() => setConfirmDelete(false)}
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </span>
        </td>
      </tr>

      {/* Expanded transaction history */}
      {isExpanded && (
        <tr>
          <td colSpan={11} className="px-4 py-3 bg-[var(--glass-row-alt)] rounded-lg">
            <h4 className="font-semibold text-base text-text-primary mb-2">Transaction History</h4>
            {transactions.length === 0 ? (
              <p className="text-text-muted text-base">No transactions found</p>
            ) : (
              <table className="w-full text-base">
                <thead>
                  <tr className="text-text-muted">
                    <th className="text-left py-1 px-2">Date</th>
                    <th className="text-left py-1 px-2">Type</th>
                    <th className="text-right py-1 px-2">Qty</th>
                    <th className="text-right py-1 px-2">Price</th>
                    <th className="text-right py-1 px-2">Total</th>
                    <th className="text-right py-1 px-2">Tax</th>
                    <th className="text-left py-1 px-2">Notes</th>
                    {(onUpdateTransaction || onDeleteTransaction) && (
                      <th className="text-center py-1 px-2"></th>
                    )}
                  </tr>
                </thead>
                <tbody>
                  {transactions.map((t) => (
                    editingTx === t.id ? (
                      <tr key={t.id} className="border-t bg-[var(--glass-primary-soft)]">
                        <td className="py-1 px-2">
                          <input
                            type="date"
                            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[8px] px-2 py-1 text-base w-32"
                            value={editTxData.date}
                            onChange={(e) => setEditTxData({ ...editTxData, date: e.target.value })}
                          />
                        </td>
                        <td className="py-1 px-2 capitalize">{t.type}</td>
                        <td className="py-1 px-2 text-right">
                          {t.type === "dividend" || t.quantity == null ? (
                            <span>{t.quantity ?? "—"}</span>
                          ) : (
                            <input
                              type="number"
                              step="any"
                              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[8px] px-2 py-1 text-base w-20 text-right"
                              value={editTxData.quantity}
                              onChange={(e) => setEditTxData({ ...editTxData, quantity: e.target.value })}
                            />
                          )}
                        </td>
                        <td className="py-1 px-2 text-right">
                          {t.type === "dividend" || t.quantity == null ? (
                            <span>{t.unit_price != null ? t.unit_price.toFixed(2) : "—"}</span>
                          ) : (
                            <input
                              type="number"
                              step="any"
                              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[8px] px-2 py-1 text-base w-24 text-right"
                              value={editTxData.unit_price}
                              onChange={(e) => setEditTxData({ ...editTxData, unit_price: e.target.value })}
                            />
                          )}
                        </td>
                        <td className="py-1 px-2 text-right">
                          {t.type === "dividend" || t.quantity == null ? (
                            <input
                              type="number"
                              step="any"
                              className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[8px] px-2 py-1 text-base w-24 text-right"
                              value={editTxData.total_value}
                              onChange={(e) => setEditTxData({ ...editTxData, total_value: e.target.value })}
                            />
                          ) : (
                            <span className="text-text-muted">
                              {CURRENCY_SYMBOLS[t.currency] ?? `${t.currency} `}
                              {((parseFloat(editTxData.quantity) || 0) * (parseFloat(editTxData.unit_price) || 0)).toFixed(2)}
                            </span>
                          )}
                        </td>
                        <td className="py-1 px-2 text-right">
                          <input
                            type="number"
                            step="any"
                            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[8px] px-2 py-1 text-base w-20 text-right"
                            value={editTxData.tax_amount}
                            onChange={(e) => setEditTxData({ ...editTxData, tax_amount: e.target.value })}
                          />
                        </td>
                        <td className="py-1 px-2">
                          <input
                            type="text"
                            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[8px] px-2 py-1 text-base w-32"
                            value={editTxData.notes}
                            onChange={(e) => setEditTxData({ ...editTxData, notes: e.target.value })}
                            placeholder="Notes"
                          />
                        </td>
                        <td className="py-1 px-2 text-center">
                          <span className="flex gap-1 justify-center">
                            <button
                              className="text-primary hover:opacity-80 text-xs font-medium"
                              onClick={() => saveEditTx(t)}
                            >
                              Save
                            </button>
                            <button
                              className="text-text-muted hover:opacity-80 text-xs"
                              onClick={() => setEditingTx(null)}
                            >
                              Cancel
                            </button>
                          </span>
                        </td>
                      </tr>
                    ) : (
                      <tr key={t.id} className="border-t hover:bg-[var(--glass-hover)]">
                        <td className="py-1 px-2">{t.date}</td>
                        <td className="py-1 px-2 capitalize">{t.type}</td>
                        <td className="py-1 px-2 text-right">{t.quantity != null ? t.quantity : "—"}</td>
                        <td className="py-1 px-2 text-right">
                          {t.unit_price != null
                            ? `${CURRENCY_SYMBOLS[t.currency] ?? `${t.currency} `}${t.unit_price.toFixed(2)}`
                            : "—"}
                        </td>
                        <td className="py-1 px-2 text-right">
                          {CURRENCY_SYMBOLS[t.currency] ?? `${t.currency} `}
                          {t.total_value.toFixed(2)}
                        </td>
                        <td className="py-1 px-2 text-right text-text-muted">
                          {t.tax_amount != null && t.tax_amount > 0 ? formatCurrency(t.tax_amount, t.currency) : "-"}
                        </td>
                        <td className="py-1 px-2 text-text-muted truncate max-w-[150px]">
                          {t.notes || "-"}
                        </td>
                        {(onUpdateTransaction || onDeleteTransaction) && (
                          <td className="py-1 px-2 text-center">
                            <span className="flex gap-1 justify-center">
                              {onUpdateTransaction && (
                                <button
                                  className="text-primary hover:opacity-80 text-xs font-medium"
                                  onClick={() => startEditTx(t)}
                                >
                                  Edit
                                </button>
                              )}
                              {onDeleteTransaction && (
                                <button
                                  className="text-negative hover:opacity-80 text-xs font-medium"
                                  onClick={() => handleDeleteTx(t.id)}
                                >
                                  Del
                                </button>
                              )}
                            </span>
                          </td>
                        )}
                      </tr>
                    )
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
