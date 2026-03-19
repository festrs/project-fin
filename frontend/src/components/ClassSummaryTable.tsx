import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Holding, AssetClass, Transaction } from "../types";
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
}

interface DividendClassData {
  asset_class_id: string;
  class_name: string;
  annual_income: number;
  currency: string;
}

interface DividendsResponse {
  dividends: DividendClassData[];
  total_annual_income: number;
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
): ClassSummary[] {
  const classMap = new Map(assetClasses.map((ac) => [ac.id, ac]));

  const totals = new Map<string, { value: number; currency: string }>();
  for (const h of holdings) {
    const val = h.current_value ?? h.total_cost;
    const existing = totals.get(h.asset_class_id) ?? { value: 0, currency: h.currency ?? "USD" };
    existing.value += val;
    totals.set(h.asset_class_id, existing);
  }

  let grandTotalBRL = 0;
  const classValues: { classId: string; value: number; valueBRL: number; currency: string }[] = [];
  for (const [classId, { value, currency }] of totals) {
    const valueBRL = currency === "USD" ? value * usdToBrl : value;
    grandTotalBRL += valueBRL;
    classValues.push({ classId, value, valueBRL, currency });
  }

  const summaries: ClassSummary[] = [];
  for (const { classId, value, valueBRL, currency } of classValues) {
    const ac = classMap.get(classId);
    const percentage = grandTotalBRL > 0 ? (valueBRL / grandTotalBRL) * 100 : 0;
    const targetWeight = ac?.target_weight ?? 0;
    summaries.push({
      classId,
      className: ac?.name ?? classId,
      totalValue: value,
      totalValueBRL: valueBRL,
      percentage,
      targetWeight,
      diff: percentage - targetWeight,
      currency,
    });
  }

  summaries.sort((a, b) => b.totalValueBRL - a.totalValueBRL);
  return summaries;
}

function computeManualDividendsByClass(dividends: Transaction[]): Map<string, { total: number; currency: string }> {
  const result = new Map<string, { total: number; currency: string }>();
  for (const d of dividends) {
    const existing = result.get(d.asset_class_id) ?? { total: 0, currency: d.currency };
    existing.total += d.total_value;
    result.set(d.asset_class_id, existing);
  }
  return result;
}

function getRecommendationCount(): number {
  const saved = localStorage.getItem("recommendationCount");
  return saved ? parseInt(saved, 10) : 2;
}

function computeWhereToInvest(
  summaries: ClassSummary[],
  investAmount: number,
  maxClasses: number
): Map<string, number> {
  const result = new Map<string, number>();
  if (investAmount <= 0) return result;

  const grandTotal = summaries.reduce((sum, s) => sum + s.totalValueBRL, 0);
  const newTotal = grandTotal + investAmount;

  const needs: { classId: string; needed: number }[] = [];
  for (const s of summaries) {
    if (s.targetWeight <= 0) continue;
    const idealValue = (s.targetWeight / 100) * newTotal;
    const needed = idealValue - s.totalValueBRL;
    if (needed > 0) {
      needs.push({ classId: s.classId, needed });
    }
  }

  // Limit to top N most underweight classes
  needs.sort((a, b) => b.needed - a.needed);
  const topNeeds = needs.slice(0, maxClasses);

  const totalNeeded = topNeeds.reduce((sum, n) => sum + n.needed, 0);
  if (totalNeeded <= 0) return result;

  for (const n of topNeeds) {
    const share = totalNeeded > investAmount
      ? (n.needed / totalNeeded) * investAmount
      : n.needed;
    result.set(n.classId, Math.round(share * 100) / 100);
  }

  return result;
}

function computeTopUnderweightClasses(
  summaries: ClassSummary[],
  maxClasses: number
): Set<string> {
  const underweight = summaries
    .filter((s) => s.targetWeight > 0 && s.diff < -1)
    .sort((a, b) => a.diff - b.diff) // most underweight first
    .slice(0, maxClasses);
  return new Set(underweight.map((s) => s.classId));
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
}: ClassSummaryTableProps) {
  const navigate = useNavigate();
  const [editingWeights, setEditingWeights] = useState<Map<string, string>>(new Map());
  const [saving, setSaving] = useState(false);
  const [investAmount, setInvestAmount] = useState<string>("");
  const [dividendModal, setDividendModal] = useState<{ classId: string; className: string; currency: string } | null>(null);

  if (loading) {
    return (
      <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
        <p className="text-text-muted text-base">Loading summary...</p>
      </div>
    );
  }

  const summaries = computeClassSummaries(holdings, assetClasses, usdToBrl);
  const grandTotalBRL = summaries.reduce((sum, s) => sum + s.totalValueBRL, 0);
  const manualDivByClass = computeManualDividendsByClass(manualDividends);

  // Build estimated dividend map by class ID
  const estimatedDivByClass = new Map<string, { annual_income: number; currency: string }>();
  if (estimatedDividends) {
    for (const d of estimatedDividends.dividends) {
      estimatedDivByClass.set(d.asset_class_id, {
        annual_income: d.annual_income,
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

  const parsedInvest = parseFloat(investAmount) || 0;
  const recCount = getRecommendationCount();
  const whereToInvest = computeWhereToInvest(summaries, parsedInvest, recCount);
  const topUnderweight = computeTopUnderweightClasses(summaries, recCount);

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
        <div>
          <h2 className="text-lg font-semibold text-text-primary tracking-[-0.3px]">Consolidated Portfolio</h2>
          <span className="text-base text-text-muted">USD/BRL: {usdToBrl.toFixed(2)}</span>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-base text-text-muted">Invest (R$):</label>
          <input
            type="number"
            className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-3.5 py-2.5 text-base w-28 focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
            placeholder="Amount"
            value={investAmount}
            onChange={(e) => setInvestAmount(e.target.value)}
          />
        </div>
      </div>
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
              <th className="text-center py-2 px-2">Where to Invest</th>
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
            </tr>
          </thead>
          <tbody>
            {summaries.map((s) => {
              const manualDiv = manualDivByClass.get(s.classId);
              const estimatedDiv = estimatedDivByClass.get(s.classId);
              const investSuggestion = whereToInvest.get(s.classId) ?? 0;

              const editedWeight = editingWeights.get(s.classId);
              const displayWeight = editedWeight !== undefined ? parseFloat(editedWeight) || 0 : s.targetWeight;
              const displayDiff = s.percentage - displayWeight;

              const isOver = displayDiff > 1;

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
                  <td className="py-2 px-2 text-right">
                    {isEditing ? (
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max="100"
                        className="bg-[var(--glass-card-bg)] border border-[var(--glass-border-input)] rounded-[10px] px-2.5 py-1.5 text-base w-20 text-right focus:outline-none focus:ring-2 focus:ring-[var(--glass-primary-ring)] focus:border-primary"
                        value={editedWeight ?? ""}
                        onClick={(e) => e.stopPropagation()}
                        onChange={(e) => handleWeightChange(s.classId, e.target.value)}
                      />
                    ) : (
                      <span>{s.targetWeight.toFixed(0)}%</span>
                    )}
                  </td>
                  <td className="py-2 px-2">
                    <div className="flex items-center justify-center gap-1.5">
                      {parsedInvest > 0 && investSuggestion > 0 ? (
                        <>
                          <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-[var(--glass-positive-soft)] text-positive text-xs font-bold">+</span>
                          <span className="text-positive text-base font-medium">
                            {formatValue(investSuggestion, "BRL")}
                          </span>
                        </>
                      ) : topUnderweight.has(s.classId) ? (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-[var(--glass-positive-soft)] text-positive text-xs font-bold">+</span>
                      ) : isOver ? (
                        <div className="w-12 h-4 bg-negative rounded" title={`Overweight by ${Math.abs(displayDiff).toFixed(1)}%`} />
                      ) : (
                        <span className="text-text-muted text-base">-</span>
                      )}
                    </div>
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
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            {isEditing && (
              <tr className="border-b">
                <td colSpan={7} className="py-2 px-2">
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
              <td className="py-2 px-2 text-center text-positive text-base font-medium">
                {parsedInvest > 0 ? formatValue(parsedInvest, "BRL") : ""}
              </td>
              <td className="py-2 px-2 text-right">
                {totalDivBRL > 0 ? formatValue(totalDivBRL, "BRL") : "-"}
              </td>
            </tr>
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
