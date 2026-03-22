interface PortfolioHeroCardProps {
  grandTotalBRL: number;
  loading: boolean;
}

export default function PortfolioHeroCard({ grandTotalBRL, loading }: PortfolioHeroCardProps) {
  const formattedValue = grandTotalBRL.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  return (
    <div
      className="relative overflow-hidden"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius)",
        padding: "24px",
      }}
    >
      <div className="flex justify-between items-start mb-6">
        <div>
          <p
            className="text-label"
            style={{
              fontSize: 11,
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "var(--text-tertiary)",
              marginBottom: 4,
            }}
          >
            Portfolio Value
          </p>
          {loading ? (
            <div
              className="animate-pulse"
              style={{ height: 56, width: 256, borderRadius: 8, background: "var(--surface-hover)" }}
            />
          ) : (
            <h3
              style={{
                fontSize: 56,
                fontWeight: 700,
                letterSpacing: "-0.03em",
                color: "var(--text-primary)",
                lineHeight: 1,
              }}
              className="tabular-nums"
            >
              R$ {formattedValue}
            </h3>
          )}
        </div>
        <div className="flex gap-2">
          {["1D", "1W", "1M", "1Y", "ALL"].map((period, i) => (
            <button
              key={period}
              title={i !== 2 ? "Coming soon" : undefined}
              className={`period-btn${i === 2 ? " active" : ""}`}
              disabled={i !== 2}
            >
              {period}
            </button>
          ))}
        </div>
      </div>

      {/* Placeholder chart */}
      <div className="h-48 w-full mt-4">
        <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1000 200">
          <defs>
            <filter id="hero-glow">
              <feGaussianBlur result="coloredBlur" stdDeviation="2" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
          <path
            d="M0,200 L0,150 C100,140 150,160 250,130 C350,100 450,120 550,80 C650,40 750,60 850,30 C950,0 1000,20 1000,20 L1000,200 Z"
            fill="rgba(52,199,89,0.1)"
          />
          <path
            d="M0,150 C100,140 150,160 250,130 C350,100 450,120 550,80 C650,40 750,60 850,30 C950,0 1000,20 1000,20"
            fill="none"
            stroke="#34c759"
            strokeWidth="3"
            strokeLinecap="round"
            filter="url(#hero-glow)"
          />
        </svg>
      </div>
    </div>
  );
}
