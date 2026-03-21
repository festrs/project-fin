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
    <div className="rounded-xl p-6 relative overflow-hidden" style={{ background: "var(--surface-container-low)" }}>
      <div className="flex justify-between items-start mb-6">
        <div>
          <p className="text-xs text-on-surface-variant font-medium uppercase tracking-widest mb-1"
            style={{ fontFamily: "var(--font-family-body)" }}
          >
            Portfolio Value
          </p>
          {loading ? (
            <div className="h-10 w-64 rounded animate-pulse" style={{ background: "var(--surface-container-high)" }} />
          ) : (
            <h3 className="text-4xl font-extrabold text-on-surface tracking-tighter tabular-nums">
              R$ {formattedValue}
            </h3>
          )}
        </div>
        <div className="flex gap-2">
          {["1D", "1W", "1M", "1Y", "ALL"].map((period, i) => (
            <span
              key={period}
              className={`px-3 py-1 rounded text-[10px] font-bold cursor-default ${
                i === 2 ? "text-primary" : "text-on-surface-variant"
              }`}
              style={i === 2 ? { background: "var(--surface-container-high)" } : {}}
            >
              {period}
            </span>
          ))}
        </div>
      </div>

      {/* Placeholder chart with gradient */}
      <div className="h-48 w-full mt-4">
        <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 1000 200">
          <defs>
            <linearGradient id="hero-chart-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="var(--chart-gradient-start)" stopOpacity="0.3" />
              <stop offset="100%" stopColor="var(--chart-gradient-start)" stopOpacity="0" />
            </linearGradient>
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
            fill="url(#hero-chart-gradient)"
          />
          <path
            d="M0,150 C100,140 150,160 250,130 C350,100 450,120 550,80 C650,40 750,60 850,30 C950,0 1000,20 1000,20"
            fill="none"
            stroke="var(--chart-line-stroke)"
            strokeWidth="3"
            strokeLinecap="round"
            filter="url(#hero-glow)"
          />
        </svg>
      </div>
    </div>
  );
}
