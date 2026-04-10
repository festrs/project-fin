import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { QuarantineBadge } from "./QuarantineBadge";
import { TransactionForm } from "./TransactionForm";
import { formatMoney, moneyToNumber } from "../utils/money";
import type { Holding, Transaction, QuarantineStatus, AssetClass, AssetClassType, FundamentalsScore } from "../types";
import { TransactionHistoryModal } from "./TransactionHistoryModal";

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

function formatCurrencyValue(value: number, currency?: string): string {
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
  const assetClass = assetClasses.find(ac => ac.id === assetClassId);
  const country = assetClass?.country || "US";
  const scoreMap = new Map((fundamentalsScores ?? []).map((s) => [s.symbol, s]));
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
  const getCurrency = (h: Holding) => h.total_cost.currency;
  const showValueBRL = isFixedIncome && holdings.some((h) => getCurrency(h) !== "BRL");
  const showDiv = !isFixedIncome && !isCrypto;
  const showScore = !isFixedIncome && !isCrypto;

  const toBRL = (value: number, cur: string) => {
    if (cur === "BRL") return value;
    const rate = exchangeRates[`${cur}-BRL`];
    return rate ? value * rate : value;
  };

  const [txModalSymbol, setTxModalSymbol] = useState<string | null>(null);

  const handleShowTransactions = async (symbol: string) => {
    await onFetchTransactions(symbol);
    setTxModalSymbol(symbol);
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
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold tracking-[-0.3px]" style={{ color: "var(--text-primary)" }}>Holdings</h2>
      </div>

      {transactionForm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center"
          style={{ background: "rgba(0, 0, 0, 0.7)" }}
          onClick={() => setTransactionForm(null)}
        >
          <div
            className="card-elevated w-full max-w-md"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-heading">
                {transactionForm.type === "buy" ? "Buy" : "Sell"} {transactionForm.symbol}
              </h3>
              <button
                onClick={() => setTransactionForm(null)}
                className="text-text-tertiary hover:opacity-80 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
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
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-base">
          <thead>
            <tr className="text-text-tertiary uppercase text-base tracking-wide">
              <th
                className="text-left px-3 py-2 cursor-pointer select-none hover:text-blue transition-colors"
                onClick={toggleSort}
              >
                {isFixedIncome ? "Name" : "Symbol"}
                {sortAsc === true ? " \u25B2" : sortAsc === false ? " \u25BC" : ""}
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
                        className="text-[10px] text-text-tertiary hover:opacity-80 ml-1"
                        title="Fetch scores for all stocks"
                        onClick={onRefreshAllScores}
                      >
                        {"\u21BB"}
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
              const isEditingThis = editingWeight?.symbol === h.symbol;

              return (
                <HoldingRows
                  key={h.symbol}
                  holding={h}
                  type={type}
                  quarantine={q}
                  isExpanded={false}
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
                  onRowClick={() => navigate(`/portfolio/${assetClassId}/${h.symbol}?country=${country}&type=${type}`)}
                  onShowTransactions={() => handleShowTransactions(h.symbol)}
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

      {txModalSymbol && (
        <TransactionHistoryModal
          className={txModalSymbol}
          assetClassId={assetClassId}
          symbols={[txModalSymbol]}
          onClose={() => setTxModalSymbol(null)}
        />
      )}
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
  onShowTransactions: () => void;
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
  onShowTransactions,
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

  const cur = h.total_cost.currency;
  const sym = CURRENCY_SYMBOLS[cur] ?? `${cur} `;
  const scoreColor = (v: number) =>
    v >= 90
      ? "var(--green)"
      : v >= 60
      ? "var(--orange)"
      : "var(--red)";

  const colCount = 4 + (showQty ? 1 : 0) + (showAvgPrice ? 1 : 0) + (showCurrentPrice ? 1 : 0) + (showValueBRL ? 1 : 0) + (showGainLoss ? 1 : 0) + (showDiv ? 1 : 0) + (showScore ? 1 : 0);

  const startEditTx = (t: Transaction) => {
    setEditingTx(t.id);
    setEditTxData({
      quantity: t.quantity != null ? String(t.quantity) : "",
      unit_price: t.unit_price != null ? t.unit_price.amount : "",
      total_value: t.total_value.amount,
      tax_amount: t.tax_amount != null ? t.tax_amount.amount : "",
      date: t.date,
      notes: t.notes ?? "",
    });
  };

  const saveEditTx = async (t: Transaction) => {
    if (!onUpdateTransaction) return;
    const txCurrency = t.total_value.currency;
    const isValueBased = t.quantity == null;
    const qty = isValueBased ? null : (parseFloat(editTxData.quantity) || 0);
    const price = isValueBased ? null : (parseFloat(editTxData.unit_price) || 0);
    const total = isValueBased || t.type === "dividend"
      ? parseFloat(editTxData.total_value) || 0
      : (qty ?? 0) * (price ?? 0);
    await onUpdateTransaction(t.id, {
      quantity: qty,
      unit_price: price != null ? { amount: String(price), currency: txCurrency } : null,
      total_value: { amount: String(total), currency: txCurrency },
      tax_amount: isValueBased ? null : { amount: String(parseFloat(editTxData.tax_amount) || 0), currency: txCurrency },
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

  const gainLossNum = moneyToNumber(h.gain_loss);

  return (
    <>
      <tr className="table-row hover:bg-[var(--row-hover)] cursor-pointer rounded-lg" onClick={onRowClick}>
        <td className="px-3 py-2">
          <span className="flex items-center gap-2">
            <span
              className="font-medium hover:text-blue transition-colors cursor-pointer"
              style={{ textDecoration: "none" }}
              onClick={(e) => { e.stopPropagation(); onRowClick(); }}
            >
              {h.symbol}
            </span>
            {q && (
              <QuarantineBadge
                isQuarantined={q.is_quarantined}
                endsAt={q.quarantine_ends_at}
              />
            )}
          </span>
        </td>
        {showQty && <td className="px-3 py-2 text-right">{h.quantity != null ? h.quantity : "\u2014"}</td>}
        {showAvgPrice && <td className="px-3 py-2 text-right">{h.avg_price != null ? formatMoney(h.avg_price) : "\u2014"}</td>}
        {showCurrentPrice && (
          <td className="px-3 py-2 text-right">
            {h.current_price != null ? formatMoney(h.current_price) : "-"}
          </td>
        )}
        <td className="px-3 py-2 text-right">
          {isFixedIncome
            ? formatMoney(h.current_value ?? h.total_cost)
            : h.current_value != null ? formatMoney(h.current_value) : "-"}
        </td>
        {showValueBRL && (
          <td className="px-3 py-2 text-right text-text-tertiary">
            {cur !== "BRL"
              ? formatCurrencyValue(toBRL(moneyToNumber(h.current_value ?? h.total_cost), cur), "BRL")
              : ""}
          </td>
        )}
        {showGainLoss && (
          <td className="px-3 py-2 text-right">
            {h.gain_loss != null ? (
              <span
                className={
                  gainLossNum > 0
                    ? "text-green"
                    : gainLossNum < 0
                    ? "text-red"
                    : ""
                }
              >
                {gainLossNum === 0
                  ? `${sym}0.00`
                  : gainLossNum > 0
                  ? `+${formatMoney(h.gain_loss)}`
                  : formatMoney(h.gain_loss)}
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
              className="input-field w-16 text-right"
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
          <td className="px-3 py-2 text-right text-text-tertiary">
            {dividendData && dividendData.income > 0
              ? formatCurrencyValue(dividendData.income, dividendData.currency)
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
              <span className="text-text-tertiary">\u2014</span>
            )}
          </td>
        )}
        <td className="px-3 py-2 text-center">
          <span className="flex gap-1 justify-center items-center relative">
            <button
              className="text-text-tertiary hover:text-blue transition-colors text-base px-2"
              title="Transaction history"
              onClick={(e) => {
                e.stopPropagation();
                onShowTransactions();
              }}
            >
              <span className="material-symbols-outlined text-lg">receipt_long</span>
            </button>
            <button
              className="text-green hover:opacity-80 text-base px-2 font-medium"
              onClick={(e) => {
                e.stopPropagation();
                onBuy();
              }}
            >
              Buy
            </button>
            <button
              className="text-red hover:opacity-80 text-base px-2 font-medium"
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
                  className="text-text-tertiary hover:opacity-80 text-base px-1"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowHoldingMenu(!showHoldingMenu);
                    setConfirmDelete(false);
                    setChangingAssetClass(false);
                  }}
                  title="More actions"
                >
                  {"\u00B7\u00B7\u00B7"}
                </button>
                {showHoldingMenu && (
                  <div
                    className="absolute right-0 top-8 z-20 card-elevated py-1 min-w-[180px]"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {onChangeAssetClass && !changingAssetClass && (
                      <button
                        className="w-full text-left px-3 py-2 text-base hover:bg-[var(--row-hover)]" style={{ color: "var(--text-primary)" }}
                        onClick={() => setChangingAssetClass(true)}
                      >
                        Change Asset Class
                      </button>
                    )}
                    {changingAssetClass && (
                      <div className="px-3 py-2">
                        <label className="block text-xs text-text-tertiary mb-1">Move to:</label>
                        <select
                          className="input-field w-full"
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
                        className="w-full text-left px-3 py-2 text-base text-red hover:bg-[var(--row-hover)]"
                        onClick={() => setConfirmDelete(true)}
                      >
                        Delete Holding
                      </button>
                    )}
                    {confirmDelete && (
                      <div className="px-3 py-2 space-y-1">
                        <p className="text-xs text-red">Delete all transactions for {h.symbol}?</p>
                        <div className="flex gap-2">
                          <button
                            className="bg-error text-white px-3 py-1 rounded-sm text-xs font-semibold"
                            onClick={async () => {
                              await onDeleteHolding!(h.symbol);
                              setShowHoldingMenu(false);
                            }}
                          >
                            Confirm
                          </button>
                          <button
                            className="text-text-tertiary text-xs"
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
          <td colSpan={colCount} className="px-4 py-3 bg-[var(--row-alt)] rounded-lg">
            <h4 className="font-semibold text-base mb-2" style={{ color: "var(--text-primary)" }}>Transaction History</h4>
            {transactions.length === 0 ? (
              <p className="text-text-tertiary text-base">No transactions found</p>
            ) : (
              <table className="w-full text-base">
                <thead>
                  <tr className="text-text-tertiary">
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
                      <tr key={t.id} className="border-t bg-[var(--primary-soft)]">
                        <td className="py-1 px-2">
                          <input
                            type="date"
                            className="input-field w-32"
                            value={editTxData.date}
                            onChange={(e) => setEditTxData({ ...editTxData, date: e.target.value })}
                          />
                        </td>
                        <td className="py-1 px-2 capitalize">{t.type}</td>
                        <td className="py-1 px-2 text-right">
                          {t.type === "dividend" || t.quantity == null ? (
                            <span>{t.quantity ?? "\u2014"}</span>
                          ) : (
                            <input
                              type="number"
                              step="any"
                              className="input-field w-20 text-right"
                              value={editTxData.quantity}
                              onChange={(e) => setEditTxData({ ...editTxData, quantity: e.target.value })}
                            />
                          )}
                        </td>
                        <td className="py-1 px-2 text-right">
                          {t.type === "dividend" || t.quantity == null ? (
                            <span>{t.unit_price != null ? formatMoney(t.unit_price) : "\u2014"}</span>
                          ) : (
                            <input
                              type="number"
                              step="any"
                              className="input-field w-24 text-right"
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
                              className="input-field w-24 text-right"
                              value={editTxData.total_value}
                              onChange={(e) => setEditTxData({ ...editTxData, total_value: e.target.value })}
                            />
                          ) : (
                            <span className="text-text-tertiary">
                              {CURRENCY_SYMBOLS[t.total_value.currency] ?? `${t.total_value.currency} `}
                              {((parseFloat(editTxData.quantity) || 0) * (parseFloat(editTxData.unit_price) || 0)).toFixed(2)}
                            </span>
                          )}
                        </td>
                        <td className="py-1 px-2 text-right">
                          <input
                            type="number"
                            step="any"
                            className="input-field w-20 text-right"
                            value={editTxData.tax_amount}
                            onChange={(e) => setEditTxData({ ...editTxData, tax_amount: e.target.value })}
                          />
                        </td>
                        <td className="py-1 px-2">
                          <input
                            type="text"
                            className="input-field w-32"
                            value={editTxData.notes}
                            onChange={(e) => setEditTxData({ ...editTxData, notes: e.target.value })}
                            placeholder="Notes"
                          />
                        </td>
                        <td className="py-1 px-2 text-center">
                          <span className="flex gap-1 justify-center">
                            <button
                              className="text-blue hover:opacity-80 text-xs font-medium"
                              onClick={() => saveEditTx(t)}
                            >
                              Save
                            </button>
                            <button
                              className="text-text-tertiary hover:opacity-80 text-xs"
                              onClick={() => setEditingTx(null)}
                            >
                              Cancel
                            </button>
                          </span>
                        </td>
                      </tr>
                    ) : (
                      <tr key={t.id} className="border-t hover:bg-[var(--row-hover)]">
                        <td className="py-1 px-2">{t.date}</td>
                        <td className="py-1 px-2 capitalize">{t.type}</td>
                        <td className="py-1 px-2 text-right">{t.quantity != null ? t.quantity : "\u2014"}</td>
                        <td className="py-1 px-2 text-right">
                          {t.unit_price != null
                            ? formatMoney(t.unit_price)
                            : "\u2014"}
                        </td>
                        <td className="py-1 px-2 text-right">
                          {formatMoney(t.total_value)}
                        </td>
                        <td className="py-1 px-2 text-right text-text-tertiary">
                          {t.tax_amount != null && moneyToNumber(t.tax_amount) > 0 ? formatMoney(t.tax_amount) : "-"}
                        </td>
                        <td className="py-1 px-2 text-text-tertiary truncate max-w-[150px]">
                          {t.notes || "-"}
                        </td>
                        {(onUpdateTransaction || onDeleteTransaction) && (
                          <td className="py-1 px-2 text-center">
                            <span className="flex gap-1 justify-center">
                              {onUpdateTransaction && (
                                <button
                                  className="text-blue hover:opacity-80 text-xs font-medium"
                                  onClick={() => startEditTx(t)}
                                >
                                  Edit
                                </button>
                              )}
                              {onDeleteTransaction && (
                                <button
                                  className="text-red hover:opacity-80 text-xs font-medium"
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
