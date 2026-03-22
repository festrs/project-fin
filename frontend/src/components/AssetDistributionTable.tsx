import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { Holding, AssetClass, Transaction, DividendsResponse } from "../types";
import { moneyToNumber } from "../utils/money";
import { computeClassSummaries, type ClassSummary } from "./ClassSummaryTable";
import { DividendHistoryModal } from "./DividendHistoryModal";

interface AssetDistributionTableProps {
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

// Icon + color mapping for asset class types
function getClassIcon(ac: AssetClass): { icon: string; color: string; bg: string } {
  if (ac.is_emergency_reserve) {
    return { icon: "savings", color: "var(--class-emergency)", bg: "rgba(251, 191, 36, 0.1)" };
  }
  if (ac.type === "crypto") {
    return { icon: "currency_bitcoin", color: "var(--class-crypto)", bg: "rgba(191, 90, 242, 0.1)" };
  }
  if (ac.type === "fixed_income") {
    return { icon: "account_balance", color: "var(--class-fixed-income)", bg: "rgba(255, 159, 10, 0.1)" };
  }
  // Stock types
  if (ac.country === "US") {
    return { icon: "public", color: "var(--class-us)", bg: "rgba(10, 132, 255, 0.1)" };
  }
  return { icon: "apartment", color: "var(--class-br)", bg: "rgba(59, 130, 246, 0.1)" };
}

function formatValue(value: number, currency: string): string {
  if (currency === "BRL") {
    return `R$ ${value.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }
  return `$ ${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
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

export default function AssetDistributionTable({
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
}: AssetDistributionTableProps) {
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
      <div className="rounded-xl p-6" style={{ background: "var(--surface)" }}>
        <p className="text-text-tertiary text-sm">Loading...</p>
      </div>
    );
  }

  const { regular: summaries, reserve: reserveSummary, grandTotalBRL } = computeClassSummaries(holdings, assetClasses, usdToBrl);
  const manualDivByClass = computeManualDividendsByClass(manualDividends);

  const estimatedDivByClass = new Map<string, { annual_income: number; currency: string }>();
  if (estimatedDividends) {
    for (const d of estimatedDividends.dividends) {
      estimatedDivByClass.set(d.asset_class_id, {
        annual_income: parseFloat(d.annual_income.amount),
        currency: d.currency,
      });
    }
  }

  // Total dividends in BRL
  let totalDivBRL = 0;
  for (const s of summaries) {
    const manual = manualDivByClass.get(s.classId);
    const estimated = estimatedDivByClass.get(s.classId);
    if (manual) totalDivBRL += manual.currency === "USD" ? manual.total * usdToBrl : manual.total;
    if (estimated) totalDivBRL += estimated.currency === "USD" ? estimated.annual_income * usdToBrl : estimated.annual_income;
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
    for (const s of summaries) initial.set(s.classId, String(s.targetWeight));
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

  const handleCancel = () => setEditingWeights(new Map());

  const classMap = new Map(assetClasses.map((ac) => [ac.id, ac]));

  // Combine all summaries for rendering (regular + reserve)
  const allSummaries: ClassSummary[] = [...summaries];
  if (reserveSummary) allSummaries.push(reserveSummary);

  const grandTotalWithReserve = grandTotalBRL + (reserveSummary?.totalValueBRL ?? 0);

  function getDividendDisplay(s: ClassSummary): React.ReactNode {
    const estimatedDiv = estimatedDivByClass.get(s.classId);
    const manualDiv = manualDivByClass.get(s.classId);

    if (manualDiv && manualDiv.total > 0) {
      return <span style={{ color: "var(--green)" }}>{formatValue(manualDiv.total, manualDiv.currency)}</span>;
    }
    if (estimatedDiv && estimatedDiv.annual_income > 0) {
      return <span style={{ color: "var(--green)" }}>{formatValue(estimatedDiv.annual_income, estimatedDiv.currency)}<span className="text-text-tertiary ml-0.5">~</span></span>;
    }
    return <span style={{ color: "var(--text-secondary)" }}>—</span>;
  }

  return (
    <div className="rounded-xl overflow-hidden" style={{ background: "var(--surface)" }}>
      {/* Header */}
      <div className="px-6 py-4 flex justify-between items-center border-b border-[var(--card-border)]">
        <div className="flex items-center gap-3">
          <h3 className="font-bold" style={{ color: "var(--text-primary)" }}>Asset Distribution</h3>
          <span className="text-xs text-text-tertiary font-body">
            USD/BRL: {usdToBrl.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {onUpdateTargetWeight && !isEditing && (
            <button
              onClick={handleStartEditing}
              className="text-blue text-xs font-bold uppercase tracking-widest flex items-center gap-1 font-body"
            >
              <span className="material-symbols-outlined text-sm">edit</span> Edit Targets
            </button>
          )}
          {onCreateClass && (
            <button
              onClick={() => setShowCreateForm((v) => !v)}
              className="text-blue text-xs font-bold uppercase tracking-widest flex items-center gap-1 font-body"
            >
              <span className="material-symbols-outlined text-sm">add</span> Add Class
            </button>
          )}
          {onCreateClass && !hasEmergencyReserve && (
            <button
              onClick={async () => {
                if (window.confirm("Create Emergency Reserve class?")) {
                  await onCreateClass("Emergency Reserve", 0, "fixed_income", true, "BR");
                }
              }}
              className="text-xs text-text-tertiary hover:text-blue transition-colors font-body"
            >
              + Reserve
            </button>
          )}
        </div>
      </div>

      {/* Create form */}
      {showCreateForm && onCreateClass && (
        <div className="px-6 py-3 flex items-center gap-2 border-b border-[var(--card-border)]">
          <input type="text" placeholder="Class name" className="input-field" value={newName} onChange={(e) => setNewName(e.target.value)} />
          <select className="input-field" value={newType} onChange={(e) => setNewType(e.target.value as "stock" | "crypto" | "fixed_income")}>
            <option value="stock">Stock</option>
            <option value="crypto">Crypto</option>
            <option value="fixed_income">Fixed Income</option>
          </select>
          <input type="number" placeholder="Target %" className="input-field w-24" value={newWeight} onChange={(e) => setNewWeight(e.target.value)} />
          <button
            disabled={creating || !newName.trim()}
            onClick={async () => {
              setCreating(true);
              try {
                await onCreateClass(newName.trim(), parseFloat(newWeight) || 0, newType);
                setNewName(""); setNewWeight(""); setNewType("stock"); setShowCreateForm(false);
              } finally { setCreating(false); }
            }}
            className="btn-primary disabled:opacity-50 whitespace-nowrap"
          >
            {creating ? "Saving..." : "Save"}
          </button>
          <button onClick={() => { setShowCreateForm(false); setNewName(""); setNewWeight(""); }} className="btn-ghost whitespace-nowrap">Cancel</button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="text-[10px] uppercase tracking-widest font-body" style={{ color: "var(--text-secondary)" }}>
              <th className="px-6 py-4 font-semibold">Asset Class</th>
              <th className="px-6 py-4 font-semibold text-right">Total Value</th>
              <th className="px-6 py-4 font-semibold text-right">Value (BRL)</th>
              <th className="px-6 py-4 font-semibold text-center">Actual %</th>
              <th className="px-6 py-4 font-semibold text-center">Target %</th>
              <th className="px-6 py-4 font-semibold text-right">
                <div className="flex items-center justify-end gap-1">
                  Annual Dividends
                  {onScrapeDividends && (
                    <button
                      onClick={onScrapeDividends}
                      disabled={scrapingDividends}
                      className="text-text-tertiary hover:text-blue transition-colors disabled:opacity-50"
                      title={scrapingDividends ? "Scraping..." : "Refresh dividends"}
                    >
                      <span className={`material-symbols-outlined text-sm ${scrapingDividends ? "animate-spin" : ""}`}>refresh</span>
                    </button>
                  )}
                </div>
              </th>
              {onDeleteClass && <th className="px-3 py-4" />}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--card-border)]">
            {allSummaries.map((s) => {
              const ac = classMap.get(s.classId);
              const iconInfo = ac ? getClassIcon(ac) : { icon: "folder", color: "var(--text-secondary)", bg: "var(--surface-hover)" };
              const editedWeight = editingWeights.get(s.classId);

              return (
                <tr
                  key={s.classId}
                  className="transition-colors cursor-pointer group hover:bg-[var(--row-hover)]"
                  onClick={() => navigate(`/portfolio/${s.classId}`)}
                >
                  <td className="px-6 py-5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded flex items-center justify-center" style={{ background: iconInfo.bg, color: iconInfo.color }}>
                        <span className="material-symbols-outlined text-lg">{iconInfo.icon}</span>
                      </div>
                      <span className="text-sm font-medium font-body">{s.className}</span>
                    </div>
                  </td>
                  <td className="px-6 py-5 text-right tabular-nums text-sm font-body">
                    {formatValue(s.totalValue, s.currency)}
                  </td>
                  <td className="px-6 py-5 text-right tabular-nums text-sm font-body">
                    {formatValue(s.totalValueBRL || s.totalValue, "BRL")}
                  </td>
                  <td className="px-6 py-5 text-center">
                    {s.isEmergencyReserve ? (
                      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>—</span>
                    ) : (
                      <span className="px-2 py-1 rounded text-[11px] font-bold tabular-nums font-body" style={{ background: "var(--surface-hover)" }}>
                        {s.percentage.toFixed(1)}%
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-5 text-center" onClick={isEditing ? (e) => e.stopPropagation() : undefined}>
                    {s.isEmergencyReserve ? (
                      <span className="text-sm" style={{ color: "var(--text-secondary)" }}>—</span>
                    ) : isEditing ? (
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max="100"
                        className="w-14 bg-transparent border-none text-center p-0 text-sm font-bold text-green focus:ring-0 font-body"
                        value={editedWeight ?? ""}
                        onClick={(e) => e.stopPropagation()}
                        onMouseDown={(e) => e.stopPropagation()}
                        onChange={(e) => handleWeightChange(s.classId, e.target.value)}
                      />
                    ) : (
                      <input
                        type="number"
                        className="w-14 bg-transparent border-none text-center p-0 text-sm font-bold text-green focus:ring-0 cursor-pointer font-body"
                        value={s.targetWeight}
                        readOnly
                        tabIndex={-1}
                      />
                    )}
                  </td>
                  <td
                    className="px-6 py-5 text-right tabular-nums text-sm font-body"
                    onClick={(e) => {
                      e.stopPropagation();
                      const hasDiv = estimatedDivByClass.has(s.classId) || manualDivByClass.has(s.classId);
                      if (hasDiv) setDividendModal({ classId: s.classId, className: s.className, currency: s.currency });
                    }}
                  >
                    {getDividendDisplay(s)}
                  </td>
                  {onDeleteClass && (
                    <td className="px-3 py-5 text-center">
                      <button
                        className="text-text-tertiary hover:text-red transition-colors opacity-0 group-hover:opacity-100"
                        title="Delete class"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`Delete asset class "${s.className}"?`)) onDeleteClass(s.classId);
                        }}
                      >
                        <span className="material-symbols-outlined text-lg">delete</span>
                      </button>
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
          <tfoot>
            {isEditing && (
              <tr className="border-b border-[var(--card-border)]">
                <td colSpan={onDeleteClass ? 7 : 6} className="px-6 py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-2 rounded overflow-hidden" style={{ background: "var(--surface-hover)" }}>
                          <div
                            className="h-full rounded transition-all"
                            style={{ background: Math.abs(totalTargetWeight - 100) < 0.5 ? "var(--green)" : "var(--orange)", width: `${Math.min(totalTargetWeight, 100)}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium font-body" style={{ color: Math.abs(totalTargetWeight - 100) < 0.5 ? "var(--green)" : "var(--orange)" }}>
                          {totalTargetWeight.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <button onClick={handleSave} disabled={saving} className="btn-primary disabled:opacity-50">{saving ? "Saving..." : "Save"}</button>
                    <button onClick={handleCancel} className="btn-ghost">Cancel</button>
                  </div>
                </td>
              </tr>
            )}
            <tr style={{ background: "rgba(44, 44, 46, 0.3)" }}>
              <td className="px-6 py-6 font-bold text-sm font-body">Grand Total</td>
              <td className="px-6 py-6 text-right font-extrabold text-xl tabular-nums" style={{ color: "var(--blue)" }} colSpan={2}>
                {formatValue(grandTotalWithReserve, "BRL")}
              </td>
              <td className="px-6 py-6 text-center text-sm font-bold tabular-nums font-body">100%</td>
              <td className="px-6 py-6 text-center text-sm font-bold tabular-nums font-body">
                {(isEditing ? totalTargetWeight : summaries.reduce((sum, s) => sum + s.targetWeight, 0)).toFixed(0)}%
              </td>
              <td className="px-6 py-6 text-right text-sm font-bold tabular-nums font-body" style={{ color: "var(--green)" }}>
                {totalDivBRL > 0 ? formatValue(totalDivBRL, "BRL") : "—"}
              </td>
              {onDeleteClass && <td className="px-3 py-6" />}
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
