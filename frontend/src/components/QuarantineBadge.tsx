interface QuarantineBadgeProps {
  isQuarantined: boolean;
  endsAt?: string | null;
}

export function QuarantineBadge({ isQuarantined, endsAt }: QuarantineBadgeProps) {
  if (!isQuarantined) return null;

  const title = endsAt
    ? `Quarantined until ${new Date(endsAt).toLocaleDateString()}`
    : "Quarantined";

  return (
    <span
      className="bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full text-xs font-medium"
      title={title}
    >
      Quarantined
    </span>
  );
}
