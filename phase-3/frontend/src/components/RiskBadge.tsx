import type { RiskClass } from "../types";

interface RiskBadgeProps {
  level: RiskClass | string;
}

export function RiskBadge({ level }: RiskBadgeProps): JSX.Element {
  const normalized = level.includes("High") ? "High" : level.includes("Uncertain") ? "Uncertain" : "Low";
  const className =
    normalized === "High"
      ? "border-risk-highBorder bg-risk-highBg text-risk-highText"
      : normalized === "Uncertain"
        ? "border-risk-uncertainBorder bg-risk-uncertainBg text-risk-uncertainText"
        : "border-risk-lowBorder bg-risk-lowBg text-risk-lowText";

  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold uppercase ${className}`}>
      {normalized}
    </span>
  );
}
