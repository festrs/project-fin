import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useFundamentals } from "../hooks/useFundamentals";
import type { FundamentalsScore } from "../types";

type Filter = "All" | "US" | "BR";

const RATING_COLOR = {
  green: "var(--green)",
  yellow: "var(--orange)",
  red: "var(--red)",
};

const RATING_WIDTH = {
  green: 100,
  yellow: 60,
  red: 25,
};

function getBadge(score: number): { label: string; cls: string } {
  if (score >= 80) return { label: "Strong Buy", cls: "badge-green" };
  if (score >= 65) return { label: "Buy", cls: "badge-green" };
  if (score >= 50) return { label: "Hold", cls: "badge-orange" };
  return { label: "Sell", cls: "badge-red" };
}

function getScoreColor(score: number): string {
  if (score >= 70) return "var(--green)";
  if (score >= 50) return "var(--orange)";
  return "var(--red)";
}

function isBR(symbol: string): boolean {
  return symbol.endsWith(".SA");
}

function ScoreBar({
  label,
  value,
  rating,
}: {
  label: string;
  value: string;
  rating: "green" | "yellow" | "red";
}) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 4,
        }}
      >
        <span style={{ fontSize: 11, color: "var(--text-tertiary)" }}>
          {label}
        </span>
        <span
          style={{
            fontSize: 11,
            fontWeight: 500,
            color: RATING_COLOR[rating],
          }}
        >
          {value}
        </span>
      </div>
      <div className="score-bar">
        <div
          className="score-bar-fill"
          style={{
            width: `${RATING_WIDTH[rating]}%`,
            background: RATING_COLOR[rating],
          }}
        />
      </div>
    </div>
  );
}

function ScoreCard({ score }: { score: FundamentalsScore }) {
  const navigate = useNavigate();
  const badge = getBadge(score.composite_score);
  const scoreColor = getScoreColor(score.composite_score);

  return (
    <div
      className="card"
      style={{ cursor: "pointer" }}
      onClick={() => navigate(`/fundamentals/${score.symbol}`)}
    >
      {/* Top row: symbol + badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 12,
        }}
      >
        <span style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
          {score.symbol.replace(".SA", "")}
        </span>
        <span className={`badge ${badge.cls}`}>{badge.label}</span>
      </div>

      {/* Large score */}
      <div
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: scoreColor,
          marginBottom: 16,
          lineHeight: 1,
        }}
      >
        {score.composite_score}
        <span style={{ fontSize: 16, fontWeight: 500, color: "var(--text-tertiary)", marginLeft: 2 }}>
          /100
        </span>
      </div>

      {/* Score bars */}
      <ScoreBar
        label="IPO Age"
        value={score.ipo_years != null ? `${score.ipo_years} yrs` : "N/A"}
        rating={score.ipo_rating}
      />
      <ScoreBar
        label="EPS Growth"
        value={score.eps_growth_pct != null ? `${score.eps_growth_pct.toFixed(1)}%` : "N/A"}
        rating={score.eps_rating}
      />
      <ScoreBar
        label="Net Debt/EBITDA"
        value={
          score.current_net_debt_ebitda != null
            ? score.current_net_debt_ebitda.toFixed(2)
            : "N/A"
        }
        rating={score.debt_rating}
      />
      <ScoreBar
        label="Profitability"
        value={
          score.profitable_years_pct != null
            ? `${score.profitable_years_pct.toFixed(0)}%`
            : "N/A"
        }
        rating={score.profit_rating}
      />
    </div>
  );
}

export default function FundamentalsIndex() {
  const { scores, loading } = useFundamentals();
  const navigate = useNavigate();
  const [filter, setFilter] = useState<Filter>("All");

  const filtered = scores.filter((s) => {
    if (filter === "BR") return isBR(s.symbol);
    if (filter === "US") return !isBR(s.symbol);
    return true;
  });

  const sorted = [...filtered].sort((a, b) => b.composite_score - a.composite_score);

  return (
    <div>
      {/* Header */}
      <div className="text-label" style={{ marginBottom: 8 }}>
        Fundamentals
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 24,
        }}
      >
        <h1
          style={{
            fontSize: 32,
            fontWeight: 700,
            letterSpacing: "-0.02em",
            color: "var(--text-primary)",
            margin: 0,
          }}
        >
          Stock Scores
        </h1>

        {/* Segmented filter */}
        <div
          style={{
            display: "flex",
            gap: 4,
            background: "rgba(255,255,255,0.06)",
            borderRadius: "var(--radius-pill)",
            padding: 3,
          }}
        >
          {(["All", "US", "BR"] as Filter[]).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: "6px 18px",
                borderRadius: "var(--radius-pill)",
                fontSize: 13,
                fontWeight: 500,
                color: filter === f ? "var(--text-primary)" : "var(--text-secondary)",
                background: filter === f ? "rgba(255,255,255,0.12)" : "transparent",
                border: "none",
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="card">
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>Loading...</p>
        </div>
      )}

      {/* Empty state */}
      {!loading && sorted.length === 0 && (
        <div className="card">
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            No fundamentals data available.
          </p>
        </div>
      )}

      {/* Score cards grid */}
      {!loading && sorted.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 16,
            marginBottom: 32,
          }}
        >
          {sorted.map((s) => (
            <ScoreCard key={s.symbol} score={s} />
          ))}
        </div>
      )}

      {/* Rankings table */}
      {!loading && sorted.length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>
              Rankings
            </span>
          </div>

          {/* Table header */}
          <div
            className="table-header"
            style={{ gridTemplateColumns: "40px 1fr 80px 100px" }}
          >
            <span>#</span>
            <span>Asset</span>
            <span style={{ textAlign: "right" }}>Score</span>
            <span style={{ textAlign: "right" }}>Rating</span>
          </div>

          {/* Table rows */}
          {sorted.map((s, i) => {
            const badge = getBadge(s.composite_score);
            const scoreColor = getScoreColor(s.composite_score);
            return (
              <div
                key={s.symbol}
                className="table-row"
                style={{ gridTemplateColumns: "40px 1fr 80px 100px" }}
                onClick={() => navigate(`/fundamentals/${s.symbol}`)}
              >
                <span style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
                  {i + 1}
                </span>
                <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                  {s.symbol.replace(".SA", "")}
                  {isBR(s.symbol) && (
                    <span
                      style={{
                        marginLeft: 6,
                        fontSize: 10,
                        color: "var(--text-tertiary)",
                      }}
                    >
                      BR
                    </span>
                  )}
                </span>
                <span
                  style={{
                    textAlign: "right",
                    fontWeight: 700,
                    color: scoreColor,
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {s.composite_score}
                </span>
                <span style={{ textAlign: "right" }}>
                  <span className={`badge ${badge.cls}`}>{badge.label}</span>
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
