import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import AssetGlyph from "./AssetGlyph";
import Icon from "./Icon";

interface Recommendation {
  symbol: string;
  class_name: string;
  diff: number;
}

export default function BuyRecommendationCard() {
  const [rec, setRec] = useState<Recommendation | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<{ recommendations: Recommendation[] }>("/recommendations", { params: { count: 1 } })
      .then((res) => {
        if (res.data.recommendations.length > 0) {
          setRec(res.data.recommendations[0]);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ background: "var(--bg-2)", border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Top recommendation</h3>
      </div>
      {loading ? (
        <div className="animate-pulse" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ height: 16, width: 200, borderRadius: 4, background: "var(--bg-3)" }} />
          <div style={{ height: 14, width: 300, borderRadius: 4, background: "var(--bg-3)" }} />
        </div>
      ) : rec ? (
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <AssetGlyph sym={rec.symbol} size={36} />
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 15, fontWeight: 600 }}>{rec.symbol}</div>
            <div style={{ fontSize: 12, color: "var(--fg-3)", marginTop: 2 }}>
              {rec.class_name} · Under-allocated {Math.abs(rec.diff).toFixed(1)}%
            </div>
          </div>
          <Link
            to="/invest"
            style={{
              all: "unset",
              cursor: "pointer",
              padding: "6px 14px",
              borderRadius: "var(--radius)",
              border: "1px solid var(--line)",
              fontSize: 12,
              fontWeight: 500,
              color: "var(--fg-2)",
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <Icon name="chevron" size={12} />
            Invest
          </Link>
        </div>
      ) : (
        <p style={{ color: "var(--fg-3)", fontSize: 13 }}>Portfolio is balanced. No buy recommendations.</p>
      )}
    </div>
  );
}
