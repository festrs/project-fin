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
      className="badge badge-warning"
      title={title}
    >
      Quarantined
    </span>
  );
}
