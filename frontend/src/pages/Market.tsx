export default function Market() {
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
          marginBottom: 16,
        }}
      >
        Market Overview
      </h1>
      <div className="card">
        <p style={{ color: "var(--text-secondary)", fontSize: 14 }}>
          Market data and news feed coming soon.
        </p>
      </div>
    </div>
  );
}
