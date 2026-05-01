import type { FeatureImpact } from "../types";

interface ShapChartProps {
  features: FeatureImpact[];
}

export function ShapChart({ features }: ShapChartProps): JSX.Element {
  const max = Math.max(...features.map((feature) => Math.abs(feature.shap_value)), 0.01);

  return (
    <div className="space-y-3">
      {features.slice(0, 5).map((feature) => {
        const width = `${Math.max((Math.abs(feature.shap_value) / max) * 48, 8)}%`;
        const positive = feature.shap_value >= 0;
        return (
          <div key={`${feature.feature}-${feature.shap_value}`} className="grid grid-cols-[minmax(0,1fr)_1.3fr_72px] items-center gap-3">
            <div className="truncate text-[13px] text-gray-600" title={feature.feature}>
              {feature.feature}
            </div>
            <div className="relative h-5 rounded bg-gray-100">
              <div className="absolute left-1/2 top-0 h-full w-px bg-gray-300" />
              <div
                className={`absolute top-1 h-3 rounded ${positive ? "left-1/2 bg-risk-highBorder" : "right-1/2 bg-risk-lowBorder"}`}
                style={{ width }}
              />
            </div>
            <div className={`text-right text-[13px] ${positive ? "text-risk-highText" : "text-risk-lowText"}`}>
              {positive ? "+" : ""}
              {feature.shap_value.toFixed(2)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
