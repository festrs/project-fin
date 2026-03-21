interface TopAppBarProps {
  title: string;
}

export default function TopAppBar({ title }: TopAppBarProps) {
  return (
    <header
      className="fixed top-0 right-0 w-[calc(100%-16rem)] h-16 z-40 flex items-center justify-between px-8"
      style={{
        background: "var(--glass-bg)",
        backdropFilter: "blur(var(--glass-blur))",
        borderBottom: "1px solid var(--glass-border)",
      }}
    >
      <h2 className="font-bold text-lg text-on-surface">{title}</h2>
      <div className="flex items-center gap-5">
        <button className="text-text-muted hover:text-on-surface-variant transition-colors cursor-pointer">
          <span className="material-symbols-outlined">notifications</span>
        </button>
        <button className="text-text-muted hover:text-on-surface-variant transition-colors cursor-pointer">
          <span className="material-symbols-outlined">account_circle</span>
        </button>
      </div>
    </header>
  );
}
