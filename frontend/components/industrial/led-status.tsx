interface LedStatusProps {
  label: string;
  tone?: "red" | "green" | "amber";
  active?: boolean;
  compact?: boolean;
}

export function LedStatus({
  label,
  tone = "red",
  active = true,
  compact = false,
}: LedStatusProps) {
  return (
    <span className={`ledStatus ${compact ? "ledStatusCompact" : ""}`}>
      <span
        className={`ledDot ledDot-${tone} ${active ? "ledDotActive" : ""}`}
        aria-hidden="true"
      />
      <span className="techLabel">{label}</span>
    </span>
  );
}
