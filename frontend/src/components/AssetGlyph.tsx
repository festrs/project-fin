const ASSET_COLORS: Record<string, string> = {
  BTC: "#f7931a",
  ETH: "#627eea",
  SOL: "#9945ff",
  LINK: "#2a5ada",
  AAPL: "#6b6b6b",
  NVDA: "#76b900",
  VOO: "#aa3030",
  QQQ: "#2060d0",
  DOGE: "#c2a633",
  AVAX: "#e84142",
  TSLA: "#cc0000",
  MSTR: "#f48024",
  IBOV: "#009b3a",
  SPX: "#1a3c7e",
  PETR4: "#007932",
  VALE3: "#4b8b3b",
  ITUB4: "#f37021",
  BBDC4: "#c4161c",
};

interface AssetGlyphProps {
  sym: string;
  size?: number;
}

export default function AssetGlyph({ sym, size = 28 }: AssetGlyphProps) {
  const bg = ASSET_COLORS[sym] || "var(--fg-2)";
  const label = sym.slice(0, 3);

  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: bg,
        color: "#fff",
        display: "grid",
        placeItems: "center",
        fontFamily: "var(--font-mono)",
        fontSize: size * 0.32,
        fontWeight: 600,
        letterSpacing: "-0.02em",
        flexShrink: 0,
      }}
    >
      {label}
    </div>
  );
}

export { ASSET_COLORS };
