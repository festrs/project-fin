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
      <div className="bg-surface-low rounded-xl p-6 border border-[var(--glass-border)]">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-3 w-20 bg-surface-high rounded mb-2" />
              <div className="h-4 w-full bg-surface-high rounded mb-1" />
              <div className="h-3 w-3/4 bg-surface-high rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface-low rounded-xl p-6 border border-[var(--glass-border)]">
      {news.length === 0 ? (
        <p className="text-text-muted text-sm" style={{ fontFamily: "var(--font-family-body)" }}>
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
              className={`block py-4 ${
                idx < Math.min(news.length, 4) - 1 ? "border-b border-[var(--glass-border)]" : ""
              } hover:opacity-80 transition-opacity`}
            >
              <p className="text-[9px] font-bold text-secondary uppercase tracking-widest mb-1"
                style={{ fontFamily: "var(--font-family-body)" }}
              >
                {item.category || item.source}
              </p>
              <h6 className="text-sm font-bold text-on-surface mb-1 line-clamp-1">
                {item.headline}
              </h6>
              <p className="text-xs text-on-surface-variant mb-2 leading-relaxed line-clamp-2"
                style={{ fontFamily: "var(--font-family-body)" }}
              >
                {item.summary}
              </p>
              <p className="text-[10px] text-on-surface-variant font-medium"
                style={{ fontFamily: "var(--font-family-body)" }}
              >
                {timeAgo(item.datetime)}
              </p>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
