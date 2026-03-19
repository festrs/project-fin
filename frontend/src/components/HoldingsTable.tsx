import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { QuarantineBadge } from "./QuarantineBadge";
import { TransactionForm } from "./TransactionForm";
import type { Holding, Transaction, QuarantineStatus, AssetClass, AssetClassType, FundamentalsScore } from "../types";

interface HoldingsTableProps {
  holdings: Holding[];
  assetClassId: string;
  assetClasses: AssetClass[];
  type: AssetClassType;
  loading: boolean;
  quarantineStatuses?: QuarantineStatus[];
  transactions: Transaction[];
  dividendsBySymbol?: Map<string, { income: number; currency: string }>;
  fundamentalsScores?: FundamentalsScore[];
  exchangeRates?: Record<string, number>;
  onRefreshAllScores?: () => Promise<void>;
  onFetchTransactions: (symbol: string) => Promise<void>;
  onCreateTransaction: (data: Omit<Transaction, "id" | "user_id" | "created_at" | "updated_at">) => Promise<unknown>;
  onUpdateTransaction?: (id: string, data: Partial<Transaction>) => Promise<unknown>;
  onDeleteTransaction?: (id: string) => Promise<unknown>;
  onDeleteHolding?: (symbol: string) => Promise<unknown>;
  onChangeAssetClass?: (symbol: string, assetClassId: string) => Promise<unknown>;
  onUpdateWeight?: (symbol: string, targetWeight: number) => Promise<unknown>;
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

export function HoldingsTable({
  holdings,
  assetClassId,
  assetClasses,
  type,
  loading,
  quarantineStatuses = [],
  transactions,
  dividendsBySymbol = new Map(),
  fundamentalsScores,
  exchangeRates = {},
  onRefreshAllScores,
  onFetchTransactions,
  onCreateTransaction,
  onUpdateTransaction,
  onDeleteTransaction,
  onDeleteHolding,
  onChangeAssetClass,
  onUpdateWeight,
}: HoldingsTableProps) {
  const navigate = useNavigate();
  const scoreMap = new Map((fundamentalsScores ?? []).map((s) => [s.symbol, s]));
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [transactionForm, setTransactionForm] = useState<{
    symbol: string;
    assetClassId: string;
    type: "buy" | "sell" | "dividend";
  } | null>(null);
  const [editingWeight, setEditingWeight] = useState<{ symbol: string; value: string } | null>(null);
  const [sortAsc, setSortAsc] = useState<boolean | null>(null);

  const quarantineMap = new Map(
    quarantineStatuses.map((q) => [q.asset_symbol, q])
  );

  const isFixedIncome = type === "fixed_income";
  const isCrypto = type === "crypto";
  const showQty = !isFixedIncome;
  const showAvgPrice = !isFixedIncome;
  const showCurrentPrice = !isFixedIncome;
  const showGainLoss = !isFixedIncome;
  const showValueBRL = isFixedIncome && holdings.some((h) => h.currency !== "BRL");
  const showDiv = !isFixedIncome && !isCrypto;
  const showScore = !isFixedIncome && !isCrypto;

  const toBRL = (value: number, cur: string) => {
    if (cur === "BRL") return value;
    const rate = exchangeRates[`${cur}-BRL`];
    return rate ? value * rate : value;
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

  const sortedHoldings = sortAsc === null
    ? holdings
    : [...holdings].sort((a, b) =>
        sortAsc
          ? a.symbol.localeCompare(b.symbol)
          : b.symbol.localeCompare(a.symbol)
      );

  const toggleSort = () => {
    setSortAsc((prev) => (prev === null ? true : prev ? false : null));
  };

  if (loading) {
    return <div>Loading holdings...</div>;
  }

  return (
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px]">Holdings</h2>
      </div>

      {transactionForm && (
        <div className="mb-4">
          <TransactionForm
            symbol={transactionForm.symbol}
            assetClassId={transactionForm.assetClassId}
            type={type}
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
              <th
                className="text-left px-3 py-2 cursor-pointer select-none hover:text-primary transition-colors"
                onClick={toggleSort}
              >
                {isFixedIncome ? "Name" : "Symbol"}
                {sortAsc === true ? " ▲" : sortAsc === false ? " ▼" : ""}
              </th>
              {showQty && <th className="text-right px-3 py-2">Qty</th>}
              {showAvgPrice && <th className="text-right px-3 py-2">Avg Price</th>}
              {showCurrentPrice && <th className="text-right px-3 py-2">Current Price</th>}
              <th className="text-right px-3 py-2">{isFixedIncome ? "Total Value" : "Current Value"}</th>
              {showValueBRL && <th className="text-right px-3 py-2">Value (R$)</th>}
              {showGainLoss && <th className="text-right px-3 py-2">Gain/Loss</th>}
              <th className="text-right px-3 py-2">Target %</th>
              <th className="text-right px-3 py-2">Actual %</th>
              {showDiv && (
                <th className="text-right px-3 py-2">Div ({new Date().getFullYear()})</th>
              )}
              {showScore && (
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
              )}
              <th className="text-center px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {sortedHoldings.map((h) => {
              const q = quarantineMap.get(h.symbol);
              const isExpanded = expandedRow === h.symbol;
              const isEditingThis = editingWeight?.symbol === h.symbol;

              return (
                <HoldingRows
                  key={h.symbol}
                  holding={h}
                  type={type}
                  quarantine={q}
                  isExpanded={isExpanded}
                  transactions={transactions}
                  classId={assetClassId}
                  isEditingWeight={isEditingThis}
                  editWeightValue={isEditingThis ? editingWeight!.value : undefined}
                  dividendData={dividendsBySymbol.get(h.symbol)}
                  score={scoreMap.get(h.symbol)}
                  assetClasses={assetClasses}
                  showValueBRL={showValueBRL}
                  toBRL={toBRL}
                  onUpdateTransaction={onUpdateTransaction}
                  onDeleteTransaction={onDeleteTransaction}
                  onDeleteHolding={onDeleteHolding}
                  onChangeAssetClass={onChangeAssetClass}
                  onFetchTransactions={onFetchTransactions}
                  onNavigateScore={() => navigate(`/fundamentals/${h.symbol}`)}
                  onRowClick={() => handleRowClick(h.symbol)}
                  onBuy={() => setTransactionForm({ symbol: h.symbol, assetClassId, type: "buy" })}
                  onSell={() => setTransactionForm({ symbol: h.symbol, assetClassId, type: "sell" })}
                  onStartEditWeight={
                    onUpdateWeight
                      ? () => setEditingWeight({ symbol: h.symbol, value: String(h.target_weight ?? 0) })
                      : undefined
                  }
                  onWeightChange={(value) => setEditingWeight((prev) => (prev ? { ...prev, value } : null))}
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

interface HoldingRowsProps {
  holding: Holding;
  type: AssetClassType;
  quarantine?: QuarantineStatus;
  isExpanded: boolean;
  transactions: Transaction[];
  classId: string;
  isEditingWeight: boolean;
  editWeightValue?: string;
  dividendData?: { income: number; currency: string };
  score?: FundamentalsScore;
  assetClasses: AssetClass[];
  showValueBRL: boolean;
  toBRL: (value: number, currency: string) => number;
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
  type,
  quarantine: q,
  isExpanded,
  transactions,
  classId,
  isEditingWeight,
  editWeightValue,
  dividendData,
  score,
  assetClasses,
  showValueBRL,
  toBRL,
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

  const isFixedIncome = type === "fixed_income";
  const isCrypto = type === "crypto";
  const showQty = !isFixedIncome;
  const showAvgPrice = !isFixedIncome;
  const showCurrentPrice = !isFixedIncome;
  const showGainLoss = !isFixedIncome;
  const showDiv = !isFixedIncome && !isCrypto;
  const showScore = !isFixedIncome && !isCrypto;

  const cur = h.currency as string;
  const sym = CURRENCY_SYMBOLS[cur] ?? `${cur} `;
  const scoreColor = (v: number) =>
    v >= 90
      ? "var(--color-positive)"
      : v >= 60
      ? "var(--color-warning)"
      : "var(--color-negative)";

  const colCount = 4 + (showQty ? 1 : 0) + (showAvgPrice ? 1 : 0) + (showCurrentPrice ? 1 : 0) + (showValueBRL ? 1 : 0) + (showGainLoss ? 1 : 0) + (showDiv ? 1 : 0) + (showScore ? 1 : 0);

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
        <td className="px-3 py-2">
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
        {showQty && <td className="px-3 py-2 text-right">{h.quantity != null ? h.quantity : "—"}</td>}
        {showAvgPrice && <td className="px-3 py-2 text-right">{h.avg_price != null ? formatCurrency(h.avg_price, cur) : "—"}</td>}
        {showCurrentPrice && (
          <td className="px-3 py-2 text-right">
            {h.current_price != null ? formatCurrency(h.current_price, cur) : "-"}
          </td>
        )}
        <td className="px-3 py-2 text-right">
          {isFixedIncome
            ? formatCurrency(h.current_value ?? h.total_cost, cur)
            : h.current_value != null ? formatCurrency(h.current_value, cur) : "-"}
        </td>
        {showValueBRL && (
          <td className="px-3 py-2 text-right text-text-muted">
            {cur !== "BRL"
              ? formatCurrency(toBRL(h.current_value ?? h.total_cost, cur), "BRL")
              : ""}
          </td>
        )}
        {showGainLoss && (
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
        )}
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
        {showDiv && (
          <td className="px-3 py-2 text-right text-text-muted">
            {dividendData && dividendData.income > 0
              ? formatCurrency(dividendData.income, dividendData.currency)
              : "-"}
          </td>
        )}
        {showScore && (
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
        )}
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
          <td colSpan={colCount} className="px-4 py-3 bg-[var(--glass-row-alt)] rounded-lg">
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
