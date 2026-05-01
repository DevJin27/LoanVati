import { Check, Loader2 } from "lucide-react";

interface ProgressStepsProps {
  activeIndex: number;
  steps: string[];
}

export function ProgressSteps({ activeIndex, steps }: ProgressStepsProps): JSX.Element {
  return (
    <div className="space-y-4">
      {steps.map((step, index) => {
        const complete = index < activeIndex;
        const active = index === activeIndex;
        return (
          <div key={step} className="flex items-center gap-3">
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                complete ? "bg-emerald-600 text-white" : active ? "bg-brand text-white" : "bg-gray-200 text-gray-500"
              }`}
            >
              {complete ? <Check className="h-4 w-4" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : index + 1}
            </span>
            <span className={`text-sm ${active ? "font-medium text-brand" : "text-gray-600"}`}>{step}</span>
          </div>
        );
      })}
    </div>
  );
}
