interface ScoreBarProps {
  score: number;
}

export function ScoreBar({ score }: ScoreBarProps): JSX.Element {
  const percent = Math.round(score * 100);
  const color = score >= 0.6 ? "bg-risk-highBorder" : score >= 0.4 ? "bg-risk-uncertainBorder" : "bg-risk-lowBorder";

  return (
    <div>
      <div className="h-3 overflow-hidden rounded-full bg-gray-200">
        <div className={`h-full rounded-full transition-all duration-700 ${color}`} style={{ width: `${percent}%` }} />
      </div>
      <div className="mt-1 text-right text-xs text-gray-500">{percent}%</div>
    </div>
  );
}
