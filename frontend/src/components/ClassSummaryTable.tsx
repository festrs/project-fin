import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Holding, AssetClass, Transaction } from "../types";
import { moneyToNumber } from "../utils/money";
import { DividendHistoryModal } from "./DividendHistoryModal";

export interface ClassSummary {
  classId: string;
  className: string;
  totalValue: number;
  totalValueBRL: number;
  percentage: number;
  targetWeight: number;
  diff: number;
  currency: string;
  isEmergencyReserve: boolean;
}

export interface ClassSummaryResult {
  regular: ClassSummary[];
  reserve: ClassSummary | null;
  grandTotalBRL: number;
}

interface DividendClassData {
  asset_class_id: string;
  class_name: string;
  annual_income: { amount: string; currency: string };
  currency: string;
}

interface DividendsResponse {
  dividends: DividendClassData[];
  total_annual_income: { amount: string; currency: string };
}

interface ClassSummaryTableProps {
  holdings: Holding[];
  assetClasses: AssetClass[];
  manualDividends: Transaction[];
  estimatedDividends: DividendsResponse | null;
  loading: boolean;
  usdToBrl: number;
  onUpdateTargetWeight?: (classId: string, weight: number) => Promise<void>;
  onScrapeDividends?: () => void;
  scrapingDividends?: boolean;
  onCreateClass?: (name: string, targetWeight: number, type: "stock" | "crypto" | "fixed_income", isEmergencyReserve?: boolean, country?: string) => Promise<unknown>;
  onDeleteClass?: (classId: string) => Promise<unknown>;
}

function formatValue(value: number, currency: string): string {
  if (currency === "BRL") {
    return `R$${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function computeClassSummaries(
  holdings: Holding[],
  assetClasses: AssetClass[],
  usdToBrl: number
): ClassSummaryResult {
  const classMap = new Map(assetClasses.map((ac) => [ac.id, ac]));

  const totals = new Map<string, { value: number; currency: string }>();
  for (const h of holdings.filter((h) => classMap.has(h.asset_class_id))) {
    const val = moneyToNumber(h.current_value ?? h.total_cost);
    const cur = h.total_cost.currency;
    const existing = totals.get(h.asset_class_id) ?? { value: 0, currency: cur };
    existing.value += val;
    totals.set(h.asset_class_id, existing);
  }

  // Separate regular and reserve values
  let grandTotalBRL = 0;
  const classValues: { classId: string; value: number; valueBRL: number; currency: string }[] = [];
  let reserveValue: { classId: string; value: number; valueBRL: number; currency: string } | null = null;

  for (const [classId, { value, currency }] of totals) {
    const ac = classMap.get(classId);
    const valueBRL = currency === "USD" ? value * usdToBrl : value;
    if (ac?.is_emergency_reserve) {
      reserveValue = { classId, value, valueBRL, currency };
    } else {
      grandTotalBRL += valueBRL;
      classValues.push({ classId, value, valueBRL, currency });
    }
  }

  const regular: ClassSummary[] = [];
  const seenClassIds = new Set<string>();

  for (const { classId, value, valueBRL, currency } of classValues) {
    const ac = classMap.get(classId);
    const percentage = grandTotalBRL > 0 ? (valueBRL / grandTotalBRL) * 100 : 0;
    const targetWeight = ac?.target_weight ?? 0;
    regular.push({
      classId,
      className: ac?.name ?? classId,
      totalValue: value,
      totalValueBRL: valueBRL,
      percentage,
      targetWeight,
      diff: percentage - targetWeight,
      currency,
      isEmergencyReserve: false,
    });
    seenClassIds.add(classId);
  }

  // Include asset classes with no holdings yet (excluding reserve)
  for (const ac of assetClasses) {
    if (!seenClassIds.has(ac.id) && !ac.is_emergency_reserve) {
      regular.push({
        classId: ac.id,
        className: ac.name,
        totalValue: 0,
        totalValueBRL: 0,
        percentage: 0,
        targetWeight: ac.target_weight,
        diff: -ac.target_weight,
        currency: "BRL",
        isEmergencyReserve: false,
      });
    }
  }

  regular.sort((a, b) => b.totalValueBRL - a.totalValueBRL);

  // Build reserve summary
  let reserve: ClassSummary | null = null;
  const reserveClass = assetClasses.find((ac) => ac.is_emergency_reserve);
  if (reserveClass) {
    reserve = {
      classId: reserveClass.id,
      className: reserveClass.name,
      totalValue: reserveValue?.value ?? 0,
      totalValueBRL: reserveValue?.valueBRL ?? 0,
      percentage: 0,
      targetWeight: 0,
      diff: 0,
      currency: reserveValue?.currency ?? "BRL",
      isEmergencyReserve: true,
    };
  }

  return { regular, reserve, grandTotalBRL };
}

function computeManualDividendsByClass(dividends: Transaction[]): Map<string, { total: number; currency: string }> {
  const result = new Map<string, { total: number; currency: string }>();
  for (const d of dividends) {
    const existing = result.get(d.asset_class_id) ?? { total: 0, currency: d.total_value.currency };
    existing.total += moneyToNumber(d.total_value);
    result.set(d.asset_class_id, existing);
  }
  return result;
}

export function ClassSummaryTable({
  holdings,
  assetClasses,
  manualDividends,
  estimatedDividends,
  loading,
  usdToBrl,
  onUpdateTargetWeight,
  onScrapeDividends,
  scrapingDividends,
  onCreateClass,
  onDeleteClass,
}: ClassSummaryTableProps) {
  const navigate = useNavigate();
  const [editingWeights, setEditingWeights] = useState<Map<string, string>>(new Map());
  const [saving, setSaving] = useState(false);
  const [dividendModal, setDividendModal] = useState<{ classId: string; className: string; currency: string } | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newWeight, setNewWeight] = useState("");
  const [newType, setNewType] = useState<"stock" | "crypto" | "fixed_income">("stock");
  const [creating, setCreating] = useState(false);

  const hasEmergencyReserve = assetClasses.some((ac) => ac.is_emergency_reserve);

  if (loading) {
    return (
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <p className="text-text-muted text-base">Loading summary...</p>
      </div>
    );
  }

  const { regular: summaries, reserve: reserveSummary, grandTotalBRL } = computeClassSummaries(holdings, assetClasses, usdToBrl);
  const manualDivByClass = computeManualDividendsByClass(manualDividends);

  // Build estimated dividend map by class ID
  const estimatedDivByClass = new Map<string, { annual_income: number; currency: string }>();
  if (estimatedDividends) {
    for (const d of estimatedDividends.dividends) {
      estimatedDivByClass.set(d.asset_class_id, {
        annual_income: parseFloat(d.annual_income.amount),
        currency: d.currency,
      });
    }
  }

  // Compute total dividends in BRL
  let totalDivBRL = 0;
  for (const s of summaries) {
    const manual = manualDivByClass.get(s.classId);
    const estimated = estimatedDivByClass.get(s.classId);
    if (manual) {
      totalDivBRL += manual.currency === "USD" ? manual.total * usdToBrl : manual.total;
    }
    if (estimated) {
      totalDivBRL += estimated.currency === "USD" ? estimated.annual_income * usdToBrl : estimated.annual_income;
    }
  }

  const isEditing = editingWeights.size > 0;
  const totalTargetWeight = summaries.reduce((sum, s) => {
    const edited = editingWeights.get(s.classId);
    return sum + (edited !== undefined ? parseFloat(edited) || 0 : s.targetWeight);
  }, 0);

  const handleWeightChange = (classId: string, value: string) => {
    setEditingWeights((prev) => {
      const next = new Map(prev);
      next.set(classId, value);
      return next;
    });
  };

  const handleStartEditing = () => {
    const initial = new Map<string, string>();
    for (const s of summaries) {
      initial.set(s.classId, String(s.targetWeight));
    }
    setEditingWeights(initial);
  };

  const handleSave = async () => {
    if (!onUpdateTargetWeight) return;
    setSaving(true);
    try {
      for (const [classId, value] of editingWeights) {
        const original = summaries.find((s) => s.classId === classId);
        const newWeight = parseFloat(value) || 0;
        if (original && newWeight !== original.targetWeight) {
          await onUpdateTargetWeight(classId, newWeight);
        }
      }
      setEditingWeights(new Map());
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setEditingWeights(new Map());
  };

  if (summaries.length === 0) {
    return (
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px] mb-3">Consolidated Portfolio</h2>
        <p className="text-text-muted text-base">No holdings data available</p>
      </div>
    );
  }

  return (
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div>
            <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px]">Consolidated Portfolio</h2>
            <span className="text-base text-text-muted">USD/BRL: {usdToBrl.toFixed(2)}</span>
          </div>
          {onCreateClass && (
            <button
              onClick={() => setShowCreateForm((v) => !v)}
              className="text-primary hover:text-primary-hover transition-colors"
              title="Add asset class"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          )}
          {onCreateClass && !hasEmergencyReserve && (
            <button
              onClick={async () => {
                if (window.confirm('Create Emergency Reserve class?')) {
                  await onCreateClass("Emergency Reserve", 0, "fixed_income", true, "BR");
                }
              }}
              className="text-xs text-text-muted hover:text-primary transition-colors border border-[var(--glass-border)] rounded-lg px-2 py-1"
              title="Add emergency reserve"
            >
              + Reserve
            </button>
          )}
        </div>
      </div>
      {showCreateForm && onCreateClass && (
        <div className="flex items-center gap-2 mb-3">
          <input
            type="text"
            placeholder="Class name"
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
          />
          <select
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            value={newType}
            onChange={(e) => setNewType(e.target.value as "stock" | "crypto" | "fixed_income")}
          >
            <option value="stock">Stock</option>
            <option value="crypto">Crypto</option>
            <option value="fixed_income">Fixed Income</option>
          </select>
          <input
            type="number"
            placeholder="Target %"
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base w-24 focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            value={newWeight}
            onChange={(e) => setNewWeight(e.target.value)}
          />
          <button
            disabled={creating || !newName.trim()}
            onClick={async () => {
              setCreating(true);
              try {
                await onCreateClass(newName.trim(), parseFloat(newWeight) || 0, newType);
                setNewName("");
                setNewWeight("");
                setNewType("stock");
                setShowCreateForm(false);
              } finally {
                setCreating(false);
              }
            }}
            className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
          >
            {creating ? "Saving..." : "Save"}
          </button>
          <button
            onClick={() => {
              setShowCreateForm(false);
              setNewName("");
              setNewWeight("");
              setNewType("stock");
            }}
            className="bg-[rgba(0,0,0,0.03)] border border-[var(--glass-border)] text-text-secondary px-4 py-2 rounded-[10px] text-base font-medium hover:bg-[rgba(0,0,0,0.06)]"
          >
            Cancel
          </button>
        </div>
      )}
      <div className="overflow-x-auto">
        <table className="w-full text-base">
          <thead>
            <tr className="text-text-muted uppercase text-base tracking-wide">
              <th className="text-left py-2 px-2">Class</th>
              <th className="text-right py-2 px-2">Total Value</th>
              <th className="text-right py-2 px-2">Total R$</th>
              <th className="text-right py-2 px-2">Actual %</th>
              <th className="text-right py-2 px-2">
                <div className="flex items-center justify-end gap-1">
                  Target %
                  {onUpdateTargetWeight && !isEditing && (
                    <button
                      onClick={handleStartEditing}
                      className="text-primary hover:text-primary-hover ml-1"
                      title="Edit targets"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                    </button>
                  )}
                </div>
              </th>
              <th className="text-right py-2 px-2">
                <div className="flex items-center justify-end gap-1">
                  Dividends ({new Date().getFullYear()})
                  {onScrapeDividends && (
                    <button
                      onClick={onScrapeDividends}
                      disabled={scrapingDividends}
                      className="text-text-muted hover:text-primary transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title={scrapingDividends ? "Scraping dividends..." : "Refresh dividends"}
                    >
                      <svg className={`w-3.5 h-3.5 ${scrapingDividends ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                    </button>
                  )}
                </div>
              </th>
              {onDeleteClass && <th className="py-2 px-2" />}
            </tr>
          </thead>
          <tbody>
            {summaries.map((s) => {
              const manualDiv = manualDivByClass.get(s.classId);
              const estimatedDiv = estimatedDivByClass.get(s.classId);

              const editedWeight = editingWeights.get(s.classId);

              // Dividend display: show estimated if available, manual if available, or both
              let divDisplay: React.ReactNode = "-";
              if (estimatedDiv && estimatedDiv.annual_income > 0) {
                divDisplay = (
                  <span title="Estimated annual dividends (Finnhub)">
                    {formatValue(estimatedDiv.annual_income, estimatedDiv.currency)}
                    <span className="text-text-muted text-base ml-0.5">~</span>
                  </span>
                );
              }
              if (manualDiv && manualDiv.total > 0) {
                divDisplay = (
                  <span>
                    {formatValue(manualDiv.total, manualDiv.currency)}
                  </span>
                );
              }

              return (
                <tr
                  key={s.classId}
                  className="even:bg-[var(--glass-row-alt)] rounded-lg cursor-pointer hover:bg-[var(--glass-hover)] transition-colors"
                  onClick={() => navigate(`/portfolio/${s.classId}`)}
                >
                  <td className="py-2 px-2 font-medium text-primary">{s.className}</td>
                  <td className="py-2 px-2 text-right">{formatValue(s.totalValue, s.currency)}</td>
                  <td className="py-2 px-2 text-right text-text-muted">
                    {s.currency === "USD"
                      ? formatValue(s.totalValueBRL, "BRL")
                      : ""}
                  </td>
                  <td className="py-2 px-2 text-right">{s.percentage.toFixed(2)}%</td>
                  <td className="py-2 px-2 text-right" onClick={isEditing ? (e) => e.stopPropagation() : undefined}>
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max="100"
                        className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-2.5 py-1.5 text-base w-20 text-right focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
                        value={editedWeight ?? ""}
                        onClick={(e) => e.stopPropagation()}
                        onMouseDown={(e) => e.stopPropagation()}
                        onChange={(e) => handleWeightChange(s.classId, e.target.value)}
                      />
                    ) : (
                      <span>{s.targetWeight.toFixed(0)}%</span>
                    )}
                  </td>
                  <td
                    className={`py-2 px-2 text-right text-text-muted ${divDisplay !== "-" ? "cursor-pointer hover:text-primary transition-colors" : ""}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (divDisplay !== "-") {
                        setDividendModal({ classId: s.classId, className: s.className, currency: s.currency });
                      }
                    }}
                  >
                    {divDisplay}
                  </td>
                  {onDeleteClass && (
                    <td className="py-2 px-2 text-center">
                      <button
                        className="text-text-muted hover:text-negative transition-colors"
                        title="Delete class"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`Delete asset class "${s.className}"?`)) {
                            onDeleteClass(s.classId);
                          }
                        }}
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            {isEditing && (
              <tr className="border-b">
                <td colSpan={onDeleteClass ? 7 : 6} className="py-2 px-2">
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 bg-[rgba(0,0,0,0.06)] rounded overflow-hidden">
                          <div
                            className={`h-full rounded transition-all ${
                              Math.abs(totalTargetWeight - 100) < 0.5 ? "bg-positive" : "bg-warning"
                            }`}
                            style={{ width: `${Math.min(totalTargetWeight, 100)}%` }}
                          />
                        </div>
                        <span className={`text-base font-medium ${
                          Math.abs(totalTargetWeight - 100) < 0.5 ? "text-positive" : "text-warning"
                        }`}>
                          {totalTargetWeight.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="bg-primary text-white px-4 py-2 rounded-[10px] text-base font-semibold hover:bg-primary-hover disabled:opacity-50"
                    >
                      {saving ? "Saving..." : "Save"}
                    </button>
                    <button
                      onClick={handleCancel}
                      className="bg-[rgba(0,0,0,0.03)] border border-[var(--glass-border)] text-text-secondary px-4 py-2 rounded-[10px] text-base font-medium hover:bg-[rgba(0,0,0,0.06)]"
                    >
                      Cancel
                    </button>
                  </div>
                </td>
              </tr>
            )}
            {reserveSummary && (
              <tr className="border-t border-[var(--glass-border)]">
                <td
                  className="py-2 px-2 font-medium text-text-secondary cursor-pointer hover:text-primary transition-colors"
                  onClick={() => navigate(`/portfolio/${reserveSummary.classId}`)}
                >
                  {reserveSummary.className}
                </td>
                <td className="py-2 px-2 text-right text-text-secondary">
                  {formatValue(reserveSummary.totalValue, reserveSummary.currency)}
                </td>
                <td className="py-2 px-2 text-right text-text-muted">
                  {reserveSummary.currency === "USD"
                    ? formatValue(reserveSummary.totalValueBRL, "BRL")
                    : ""}
                </td>
                <td className="py-2 px-2 text-right text-text-muted">-</td>
                <td className="py-2 px-2 text-right text-text-muted">-</td>
                <td className="py-2 px-2 text-center text-text-muted">-</td>
                <td className="py-2 px-2 text-right text-text-muted">-</td>
                {onDeleteClass && (
                  <td className="py-2 px-2 text-center">
                    <button
                      className="text-text-muted hover:text-negative transition-colors"
                      title="Delete emergency reserve"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Delete emergency reserve?')) {
                          onDeleteClass(reserveSummary.classId);
                        }
                      }}
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </td>
                )}
              </tr>
            )}
            <tr className="font-semibold bg-[var(--glass-primary-soft)]">
              <td className="py-2 px-2">Total</td>
              <td className="py-2 px-2" />
              <td className="py-2 px-2 text-right">
                {formatValue(grandTotalBRL, "BRL")}
              </td>
              <td className="py-2 px-2 text-right">100%</td>
              <td className="py-2 px-2 text-right">
                {(isEditing ? totalTargetWeight : summaries.reduce((sum, s) => sum + s.targetWeight, 0)).toFixed(0)}%
              </td>
              <td className="py-2 px-2 text-right">
                {totalDivBRL > 0 ? formatValue(totalDivBRL, "BRL") : "-"}
              </td>
              {onDeleteClass && <td className="py-2 px-2" />}
            </tr>
            {reserveSummary && reserveSummary.totalValueBRL > 0 && (
              <tr className="font-semibold text-text-secondary">
                <td className="py-2 px-2">Total + Reserve</td>
                <td className="py-2 px-2" />
                <td className="py-2 px-2 text-right">
                  {formatValue(grandTotalBRL + reserveSummary.totalValueBRL, "BRL")}
                </td>
                <td colSpan={onDeleteClass ? 5 : 4} className="py-2 px-2" />
              </tr>
            )}
          </tfoot>
        </table>
      </div>
      {dividendModal && (
        <DividendHistoryModal
          className={dividendModal.className}
          assetClassId={dividendModal.classId}
          currency={dividendModal.currency}
          onClose={() => setDividendModal(null)}
        />
      )}
    </div>
  );
}
