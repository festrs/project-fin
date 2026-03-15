interface ChartCardProps {
  title: string;
  children: React.ReactNode;
}

export function ChartCard({ title, children }: ChartCardProps) {
  return (
    <div className="bg-[var(--glass-card-bg)] border border-[var(--glass-border)] rounded-[14px] p-6">
      <h3 className="text-base font-semibold text-text-primary mb-4">{title}</h3>
      {children}
    </div>
  );
}
