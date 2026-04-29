import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { computeClassSummaries } from "../components/ClassSummaryTable";
import PortfolioHeroCard from "../components/PortfolioHeroCard";
import AssetDistributionTable from "../components/AssetDistributionTable";
import BuyRecommendationCard from "../components/BuyRecommendationCard";
import NewsCard from "../components/NewsCard";
import CorporateEventAlert from "../components/CorporateEventAlert";
import AssetGlyph from "../components/AssetGlyph";
import Sparkline from "../components/Sparkline";
import { usePortfolio } from "../hooks/usePortfolio";
import { useAssetClasses } from "../hooks/useAssetClasses";
import { useSplits } from "../hooks/useSplits";
import { moneyToNumber } from "../utils/money";
import type { Transaction, AssetClass, DividendsResponse, Holding } from "../types";
import api from "../services/api";

const CLASS_PALETTE = [
  "oklch(0.62 0.14 40)",
  "oklch(0.55 0.10 240)",
  "oklch(0.68 0.10 150)",
  "oklch(0.60 0.15 300)",
  "oklch(0.70 0.15 60)",
  "oklch(0.55 0.12 200)",
];

function getClassColor(_ac: AssetClass, index: number): string {
  return CLASS_PALETTE[index % CLASS_PALETTE.length];
}

function fmtMoney(n: number, compact = false): string {
  if (compact && Math.abs(n) >= 1000) {
    return "R$\u00A0" + Intl.NumberFormat("pt-BR", { notation: "compact", maximumFractionDigits: 1 }).format(n);
  }
  return "R$\u00A0" + n.toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtPct(n: number): string {
  const sign = n > 0 ? "+" : "";
  return sign + n.toFixed(2) + "%";
}

function makeSparkData(symbol: string, positive: boolean): number[] {
  let seed = 0;
  for (let i = 0; i < symbol.length; i++) seed += symbol.charCodeAt(i);
  const pts: number[] = [];
  let v = 10;
  for (let i = 0; i < 26; i++) {
    seed = (seed * 9301 + 49297) % 233280;
    v += (seed / 233280 - 0.5) * 0.6 + (positive ? 0.06 : -0.04);
    pts.push(Math.max(0.01, v));
  }
  return pts;
}

function getGainPct(h: Holding): number {
  const current = moneyToNumber(h.current_value ?? h.total_cost);
  const cost = moneyToNumber(h.total_cost);
  return cost > 0 ? ((current - cost) / cost) * 100 : 0;
}

function getDayPct(h: Holding): number {
  const price = h.current_price ? moneyToNumber(h.current_price) : 0;
  const avg = h.avg_price ? moneyToNumber(h.avg_price) : 0;
  if (avg <= 0) return 0;
  return ((price - avg) / avg) * 100;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { holdings, loading: portfolioLoading, refresh: refreshPortfolio } = usePortfolio();
  const { assetClasses, loading: classesLoading, updateClass, createClass, deleteClass } = useAssetClasses();
  const { pendingSplits, actionLoading, applySplit, dismissSplit } = useSplits();

  const [manualDividends, setManualDividends] = useState<Transaction[]>([]);
  const [estimatedDividends, setEstimatedDividends] = useState<DividendsResponse | null>(null);
  const [usdToBrl, setUsdToBrl] = useState<number>(5.15);
  const [scrapingDividends, setScrapingDividends] = useState(false);

  const fetchManualDividends = useCallback(async () => {
    try {
      const res = await api.get<Transaction[]>("/transactions");
      setManualDividends(res.data.filter((t) => t.type === "dividend"));
    } catch { /* silently fail */ }
  }, []);

  const fetchEstimatedDividends = useCallback(async () => {
    try {
      const res = await api.get<DividendsResponse>("/portfolio/dividends");
      setEstimatedDividends(res.data);
    } catch { /* silently fail */ }
  }, []);

  const fetchExchangeRate = useCallback(async () => {
    try {
      const res = await api.get<{ pair: string; rate: number }>("/portfolio/exchange-rate?pair=USD-BRL");
      setUsdToBrl(res.data.rate);
    } catch { /* keep fallback */ }
  }, []);

  useEffect(() => {
    fetchManualDividends();
    fetchEstimatedDividends();
    fetchExchangeRate();
  }, [fetchManualDividends, fetchEstimatedDividends, fetchExchangeRate]);

  const loading = portfolioLoading || classesLoading;
  const { regular: regularSummaries, reserve: reserveSummary, grandTotalBRL } = computeClassSummaries(holdings, assetClasses, usdToBrl);
  const grandTotalWithReserve = grandTotalBRL + (reserveSummary?.totalValueBRL ?? 0);

  // Build donut data
  const classMap = new Map(assetClasses.map((ac) => [ac.id, ac]));
  const donutData = regularSummaries.map((s, index) => {
    const ac = classMap.get(s.classId);
    return {
      className: s.className,
      percentage: s.percentage,
      targetWeight: s.targetWeight,
      color: ac ? getClassColor(ac, index) : "#666",
    };
  });

  // Compute total gain/loss
  const totalValue = holdings.reduce((a, h) => a + moneyToNumber(h.current_value ?? h.total_cost), 0);
  const totalCost = holdings.reduce((a, h) => a + moneyToNumber(h.total_cost), 0);
  const totalGain = totalValue - totalCost;
  const totalGainPct = totalCost > 0 ? (totalGain / totalCost) * 100 : 0;

  // Top movers - sort by day pct
  const sorted = [...holdings].sort((a, b) => getDayPct(b) - getDayPct(a));
  const movers = sorted.length > 5
    ? [...sorted.slice(0, 3), ...sorted.slice(-2).reverse()]
    : sorted;

  const handleScrapeDividends = useCallback(async () => {
    try {
      setScrapingDividends(true);
      await api.post("/dividends/scrape");
      const poll = setInterval(async () => {
        try {
          const res = await api.get<{ running: boolean }>("/dividends/scrape/status");
          if (!res.data.running) {
            clearInterval(poll);
            setScrapingDividends(false);
            fetchEstimatedDividends();
          }
        } catch { clearInterval(poll); setScrapingDividends(false); }
      }, 5000);
    } catch { setScrapingDividends(false); }
  }, [fetchEstimatedDividends]);

  const handleUpdateTargetWeight = async (classId: string, weight: number) => {
    await updateClass(classId, { target_weight: weight });
    refreshPortfolio();
  };

  const sharedCard: React.CSSProperties = {
    background: "var(--bg-2)",
    border: "1px solid var(--line)",
    borderRadius: "var(--radius)",
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
      {/* Hero chart */}
      <PortfolioHeroCard grandTotalBRL={grandTotalWithReserve} loading={loading} />

      {/* Three-up row: Allocation, P&L, Top Movers */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20 }}>
        {/* Allocation donut */}
        <div style={{ ...sharedCard, padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Allocation</h3>
            <span style={{ color: "var(--fg-3)", fontSize: 12 }}>{donutData.length} categories</span>
          </div>
          {donutData.length > 0 ? (
            <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
              <DonutMini slices={donutData} />
              <div style={{ flex: 1, display: "grid", gap: 10 }}>
                {donutData.map((s) => (
                  <div key={s.className} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color, display: "inline-block" }} />
                    <span style={{ fontSize: 13, flex: 1 }}>{s.className}</span>
                    <span className="num" style={{ fontSize: 12, color: "var(--fg-2)" }}>{s.percentage.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <p style={{ color: "var(--fg-3)", fontSize: 13 }}>No allocation data</p>
          )}
        </div>

        {/* Unrealized P&L */}
        <div style={{ ...sharedCard, padding: 24 }}>
          <div className="section-title">Unrealized P&L</div>
          {loading ? (
            <div className="animate-pulse" style={{ height: 32, width: 160, borderRadius: 6, background: "var(--bg-3)", marginTop: 8 }} />
          ) : (
            <>
              <div className="num" style={{
                fontFamily: "var(--font-display)", fontSize: 32, fontWeight: 600, letterSpacing: "-0.02em", marginTop: 8,
                color: totalGain >= 0 ? "var(--up)" : "var(--down)",
              }}>
                {totalGain >= 0 ? "+" : ""}{fmtMoney(totalGain)}
              </div>
              <div className="num" style={{ fontSize: 14, color: "var(--fg-2)", marginTop: 2 }}>
                {fmtPct(totalGainPct)} since first buy
              </div>
              <div style={{ height: 1, background: "var(--line)", margin: "16px 0" }} />
              <div style={{ display: "grid", gap: 10, fontSize: 13 }}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--fg-3)" }}>Cost basis</span>
                  <span className="num">{fmtMoney(totalCost)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--fg-3)" }}>Market value</span>
                  <span className="num">{fmtMoney(totalValue)}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--fg-3)" }}>Positions</span>
                  <span className="num">{holdings.length}</span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Top movers */}
        <div style={{ ...sharedCard, padding: 24 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Top movers</h3>
            <span style={{ color: "var(--fg-3)", fontSize: 12 }}>by return</span>
          </div>
          <div style={{ display: "grid", gap: 10 }}>
            {movers.map((h) => {
              const pct = getGainPct(h);
              const sparkData = makeSparkData(h.symbol, pct >= 0);
              return (
                <button
                  key={h.symbol}
                  onClick={() => {
                    const ac = assetClasses.find((ac) => ac.id === h.asset_class_id);
                    if (ac) navigate(`/portfolio/${ac.id}/${h.symbol}`);
                  }}
                  style={{ all: "unset", cursor: "pointer", display: "flex", alignItems: "center", gap: 10, padding: "6px 0" }}
                >
                  <AssetGlyph sym={h.symbol} size={26} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{h.symbol}</div>
                  </div>
                  <Sparkline data={sparkData} width={60} height={22} positive={pct >= 0} />
                  <div className="num" style={{
                    fontSize: 12, fontWeight: 500, minWidth: 56, textAlign: "right",
                    color: pct >= 0 ? "var(--up)" : "var(--down)",
                  }}>
                    {fmtPct(pct)}
                  </div>
                </button>
              );
            })}
            {movers.length === 0 && (
              <p style={{ color: "var(--fg-3)", fontSize: 13 }}>No holdings yet</p>
            )}
          </div>
        </div>
      </section>

      {/* Asset Distribution + Buy Recommendation + News */}
      <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }} className="wl-news">
        <div>
          <AssetDistributionTable
            holdings={holdings}
            assetClasses={assetClasses}
            manualDividends={manualDividends}
            estimatedDividends={estimatedDividends}
            loading={loading}
            usdToBrl={usdToBrl}
            onUpdateTargetWeight={handleUpdateTargetWeight}
            onScrapeDividends={handleScrapeDividends}
            scrapingDividends={scrapingDividends}
            onCreateClass={async (name, weight, type, isEmergencyReserve, country) => {
              await createClass(name, weight, type, isEmergencyReserve, country);
              refreshPortfolio();
            }}
            onDeleteClass={async (classId) => {
              await deleteClass(classId);
              refreshPortfolio();
            }}
          />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 20 }}>
          <BuyRecommendationCard />
          <NewsCard />
        </div>
      </section>

      {/* Corporate Events */}
      <CorporateEventAlert
        splits={pendingSplits}
        actionLoading={actionLoading}
        onApply={applySplit}
        onDismiss={dismissSplit}
      />
    </div>
  );
}

function DonutMini({ slices }: { slices: { className: string; percentage: number; color: string }[] }) {
  const size = 120;
  const thickness = 14;
  const total = slices.reduce((a, s) => a + s.percentage, 0);
  const r = size / 2 - thickness / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--bg-3)" strokeWidth={thickness} />
      {slices.map((s, i) => {
        const frac = total > 0 ? s.percentage / total : 0;
        const len = frac * c;
        const dash = `${len} ${c - len}`;
        const el = (
          <circle
            key={i}
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={s.color}
            strokeWidth={thickness}
            strokeDasharray={dash}
            strokeDashoffset={-offset}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            strokeLinecap="butt"
          />
        );
        offset += len;
        return el;
      })}
    </svg>
  );
}
