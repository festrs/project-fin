import { useMarketIndices } from "../hooks/useMarketIndices";
import { useMarketMovers } from "../hooks/useMarketMovers";
import { useNews, type NewsItem } from "../hooks/useNews";
import type { MarketIndex, MarketMover } from "../types";

function timeAgo(unixSeconds: number): string {
  const diff = Math.floor(Date.now() / 1000 - unixSeconds);
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function IndexCardSkeleton() {
  return (
    <div className="card" style={{ padding: 20 }}>
      <div
        className="animate-pulse"
        style={{
          height: 14,
          width: 80,
          borderRadius: 4,
          background: "var(--surface-hover)",
          marginBottom: 12,
        }}
      />
      <div
        className="animate-pulse"
        style={{
          height: 28,
          width: 120,
          borderRadius: 4,
          background: "var(--surface-hover)",
          marginBottom: 8,
        }}
      />
      <div
        className="animate-pulse"
        style={{
          height: 14,
          width: 60,
          borderRadius: 4,
          background: "var(--surface-hover)",
        }}
      />
    </div>
  );
}

function IndexCard({ index }: { index: MarketIndex }) {
  const changePct = index.change_pct;
  const color =
    changePct === null
      ? "var(--text-tertiary)"
      : changePct >= 0
        ? "#34c759"
        : "#ff3b30";
  const sign = changePct !== null && changePct >= 0 ? "+" : "";

  return (
    <div className="card" style={{ padding: 20 }}>
      <div
        style={{
          fontSize: 13,
          color: "var(--text-secondary)",
          marginBottom: 8,
        }}
      >
        {index.name}
      </div>
      <div
        style={{
          fontSize: 24,
          fontWeight: 700,
          color: "var(--text-primary)",
          letterSpacing: "-0.02em",
          marginBottom: 4,
        }}
      >
        {index.value ?? "--"}
      </div>
      <div style={{ fontSize: 14, fontWeight: 600, color }}>
        {changePct !== null ? `${sign}${changePct.toFixed(2)}%` : "--"}
      </div>
    </div>
  );
}

function MoverRow({ mover }: { mover: MarketMover }) {
  const color = mover.change_pct >= 0 ? "#34c759" : "#ff3b30";
  const sign = mover.change_pct >= 0 ? "+" : "";

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        padding: "10px 0",
        borderBottom: "1px solid var(--surface-hover)",
      }}
    >
      <div>
        <div
          style={{
            fontSize: 14,
            fontWeight: 600,
            color: "var(--text-primary)",
          }}
        >
          {mover.symbol}
        </div>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
          {mover.name}
        </div>
      </div>
      <div style={{ textAlign: "right" }}>
        <div style={{ fontSize: 14, fontWeight: 600, color }}>
          {sign}
          {mover.change_pct.toFixed(2)}%
        </div>
        <div style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
          {mover.current_price}
        </div>
      </div>
    </div>
  );
}

function MoversSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="animate-pulse"
          style={{
            height: 44,
            borderRadius: 4,
            background: "var(--surface-hover)",
          }}
        />
      ))}
    </div>
  );
}

function NewsItemRow({ item }: { item: NewsItem }) {
  return (
    <a
      href={item.url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: "block",
        padding: "14px 0",
        borderBottom: "1px solid var(--surface-hover)",
        textDecoration: "none",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 8,
          fontSize: 12,
          color: "var(--text-tertiary)",
          marginBottom: 4,
        }}
      >
        <span>{item.source}</span>
        <span>&middot;</span>
        <span>{timeAgo(item.datetime)}</span>
      </div>
      <div
        style={{
          fontSize: 14,
          fontWeight: 600,
          color: "var(--text-primary)",
          marginBottom: 4,
        }}
      >
        {item.headline}
      </div>
      {item.summary && (
        <div
          style={{
            fontSize: 13,
            color: "var(--text-secondary)",
            lineHeight: 1.4,
          }}
        >
          {item.summary}
        </div>
      )}
    </a>
  );
}

function NewsSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i}>
          <div
            className="animate-pulse"
            style={{
              height: 12,
              width: 140,
              borderRadius: 4,
              background: "var(--surface-hover)",
              marginBottom: 8,
            }}
          />
          <div
            className="animate-pulse"
            style={{
              height: 16,
              width: "80%",
              borderRadius: 4,
              background: "var(--surface-hover)",
              marginBottom: 6,
            }}
          />
          <div
            className="animate-pulse"
            style={{
              height: 13,
              width: "60%",
              borderRadius: 4,
              background: "var(--surface-hover)",
            }}
          />
        </div>
      ))}
    </div>
  );
}

export default function Market() {
  const {
    indices,
    loading: indicesLoading,
    error: indicesError,
  } = useMarketIndices();
  const {
    movers,
    loading: moversLoading,
    error: moversError,
  } = useMarketMovers();
  const { news, loading: newsLoading, error: newsError } = useNews();

  const hasMovers =
    movers.gainers.length > 0 || movers.losers.length > 0;

  return (
    <div>
      <div className="text-label" style={{ marginBottom: 8 }}>
        Market
      </div>
      <h1
        style={{
          fontSize: 32,
          fontWeight: 700,
          letterSpacing: "-0.02em",
          color: "var(--text-primary)",
          marginBottom: 24,
        }}
      >
        Market Overview
      </h1>

      {/* Index Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: 16,
          marginBottom: 24,
        }}
      >
        {indicesLoading
          ? [1, 2, 3].map((i) => <IndexCardSkeleton key={i} />)
          : indicesError
            ? (
                <div
                  className="card"
                  style={{
                    gridColumn: "1 / -1",
                    padding: 20,
                    color: "var(--text-secondary)",
                    fontSize: 14,
                  }}
                >
                  Failed to load indices.
                </div>
              )
            : indices.map((idx) => <IndexCard key={idx.symbol} index={idx} />)}
      </div>

      {/* Portfolio Movers */}
      <div className="card" style={{ padding: 20, marginBottom: 24 }}>
        <h2
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: "var(--text-primary)",
            marginBottom: 16,
          }}
        >
          Your Portfolio Movers
        </h2>
        {moversLoading ? (
          <div
            className="grid grid-cols-1 md:grid-cols-2"
            style={{ gap: 24 }}
          >
            <MoversSkeleton />
            <MoversSkeleton />
          </div>
        ) : moversError ? (
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            Failed to load movers.
          </p>
        ) : !hasMovers ? (
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            No holdings with price changes.
          </p>
        ) : (
          <div
            className="grid grid-cols-1 md:grid-cols-2"
            style={{ gap: 24 }}
          >
            <div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#34c759",
                  marginBottom: 8,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Gainers
              </div>
              {movers.gainers.length === 0 ? (
                <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
                  None
                </p>
              ) : (
                movers.gainers
                  .slice(0, 3)
                  .map((m) => <MoverRow key={m.symbol} mover={m} />)
              )}
            </div>
            <div>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#ff3b30",
                  marginBottom: 8,
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Losers
              </div>
              {movers.losers.length === 0 ? (
                <p style={{ color: "var(--text-tertiary)", fontSize: 13 }}>
                  None
                </p>
              ) : (
                movers.losers
                  .slice(0, 3)
                  .map((m) => <MoverRow key={m.symbol} mover={m} />)
              )}
            </div>
          </div>
        )}
      </div>

      {/* Market News */}
      <div className="card" style={{ padding: 20 }}>
        <h2
          style={{
            fontSize: 18,
            fontWeight: 700,
            color: "var(--text-primary)",
            marginBottom: 16,
          }}
        >
          Market News
        </h2>
        {newsLoading ? (
          <NewsSkeleton />
        ) : newsError ? (
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            Failed to load news.
          </p>
        ) : news.length === 0 ? (
          <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
            No news available.
          </p>
        ) : (
          news.map((item) => <NewsItemRow key={item.id} item={item} />)
        )}
      </div>
    </div>
  );
}
