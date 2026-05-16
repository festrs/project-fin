import { useNews } from "../hooks/useNews";
import Icon from "./Icon";

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
      <div style={{ background: "var(--bg-2)", border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 24 }}>
        <div style={{ display: "grid", gap: 16 }}>
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div style={{ height: 12, width: 80, borderRadius: 4, background: "var(--bg-3)", marginBottom: 8 }} />
              <div style={{ height: 16, width: "100%", borderRadius: 4, background: "var(--bg-3)", marginBottom: 4 }} />
              <div style={{ height: 12, width: "75%", borderRadius: 4, background: "var(--bg-3)" }} />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={{ background: "var(--bg-2)", border: "1px solid var(--line)", borderRadius: "var(--radius)", padding: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>News</h3>
        <span style={{ color: "var(--fg-3)", fontSize: 12 }}>Curated for your holdings</span>
      </div>
      {news.length === 0 ? (
        <p style={{ color: "var(--fg-3)", fontSize: 13 }}>No recent market news</p>
      ) : (
        <div style={{ display: "grid", gap: 4 }}>
          {news.slice(0, 5).map((item) => (
            <a
              key={item.id}
              href={item.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                textDecoration: "none",
                color: "inherit",
                display: "grid",
                gridTemplateColumns: "1fr auto",
                gap: 12,
                alignItems: "start",
                padding: "12px 4px",
                borderBottom: "1px solid var(--line)",
              }}
            >
              <div>
                <div style={{ fontSize: 13, lineHeight: 1.4 }}>{item.headline}</div>
                <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 4 }}>
                  <span style={{ fontWeight: 500, color: "var(--fg-2)" }}>{item.source || item.category}</span>
                  {" · "}
                  {timeAgo(item.datetime)}
                </div>
              </div>
              <Icon name="chevron" size={14} />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
