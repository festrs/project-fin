import { useNews } from "../hooks/useNews";

function timeAgo(unixTimestamp: number): string {
  const now = Math.floor(Date.now() / 1000);
  const diff = now - unixTimestamp;

  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export default function NewsCard() {
  const { news, loading } = useNews();

  if (loading) {
    return (
      <div className="card">
        <div className="card-title">Market News</div>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-3 w-24 rounded mb-2" style={{ background: "var(--surface-hover)" }} />
              <div className="h-4 w-full rounded" style={{ background: "var(--surface-hover)" }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <div className="card-title">Market News</div>
      {news.length === 0 ? (
        <p style={{ color: "var(--text-tertiary)", fontSize: 14 }}>
          No recent market news
        </p>
      ) : (
        <div>
          {news.slice(0, 4).map((item, idx) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block hover:opacity-80 transition-opacity"
              style={{
                padding: "14px 0",
                borderBottom: idx < Math.min(news.length, 4) - 1 ? "1px solid var(--border)" : "none",
              }}
            >
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "var(--text-tertiary)",
                  marginBottom: 4,
                }}
              >
                {item.source || item.category} &middot; {timeAgo(item.datetime)}
              </div>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 600,
                  lineHeight: 1.4,
                  color: "var(--text-primary)",
                }}
                className="line-clamp-2"
              >
                {item.headline}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
