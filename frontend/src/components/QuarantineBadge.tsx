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
      className="bg-[rgba(245,158,11,0.1)] text-amber-700 px-2.5 py-1 rounded-md text-base font-semibold"
      title={title}
    >
      Quarantined
    </span>
  );
}
