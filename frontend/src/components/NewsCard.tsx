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
      <div className="rounded-xl p-6" style={{ background: "var(--surface)", border: "1px solid var(--card-border)" }}>
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-3 w-20 rounded mb-2" style={{ background: "var(--surface-hover)" }} />
              <div className="h-4 w-full rounded mb-1" style={{ background: "var(--surface-hover)" }} />
              <div className="h-3 w-3/4 rounded" style={{ background: "var(--surface-hover)" }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-6" style={{ background: "var(--surface)", border: "1px solid var(--card-border)" }}>
      <h4 className="text-xs font-medium uppercase tracking-widest mb-4 font-body" style={{ color: "var(--text-tertiary)" }}>
        Market News
      </h4>
      {news.length === 0 ? (
        <p className="text-sm font-body" style={{ color: "var(--text-tertiary)" }}>
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
                idx < Math.min(news.length, 4) - 1 ? "border-b" : ""
              } hover:opacity-80 transition-opacity`}
              style={idx < Math.min(news.length, 4) - 1 ? { borderColor: "var(--card-border)" } : undefined}
            >
              <p className="text-[9px] font-bold uppercase tracking-widest mb-1 font-body" style={{ color: "var(--text-tertiary)" }}>
                {item.source || item.category}
              </p>
              <h6 className="text-sm font-bold mb-1 line-clamp-1" style={{ color: "var(--text-primary)" }}>
                {item.headline}
              </h6>
              <p className="text-xs mb-2 leading-relaxed line-clamp-2 font-body" style={{ color: "var(--text-secondary)" }}>
                {item.summary}
              </p>
              <p className="text-[10px] font-medium font-body" style={{ color: "var(--text-tertiary)" }}>
                {timeAgo(item.datetime)}
              </p>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
