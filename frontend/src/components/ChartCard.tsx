interface ChartCardProps {
  title: string;
  children: React.ReactNode;
}

export function ChartCard({ title, children }: ChartCardProps) {
  return (
    <div className="card">
      <h3 className="text-heading mb-4" style={{ fontSize: '1rem' }}>{title}</h3>
      {children}
    </div>
  );
}
