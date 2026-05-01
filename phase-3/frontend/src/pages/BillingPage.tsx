import { useEffect, useState } from "react";

import { Button } from "../components/Button";
import { api } from "../lib/api";
import { formatDate } from "../lib/format";
import type { BillingStatus } from "../types";

const plans = [
  { name: "Free", price: "₹0", features: ["10 reports per month", "Single DSA account", "ML score and report"] },
  { name: "Growth", price: "₹799", features: ["Unlimited screening", "Outcome logging", "Fix It coaching"] },
  { name: "Team", price: "₹1,999", features: ["Unlimited screening", "5 team seats", "Shared pipeline"] },
];

export function BillingPage(): JSX.Element {
  const [billing, setBilling] = useState<BillingStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.billingStatus().then((status) => {
      if (!cancelled) {
        setBilling(status);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="mx-auto max-w-5xl px-4 py-6 pb-24 md:px-8">
      <h1 className="text-[28px] font-medium tracking-normal text-gray-950">Billing & Plans</h1>

      <section className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-6">
        <div className="text-xs font-semibold uppercase tracking-[0.06em] text-brand">Current plan</div>
        <h2 className="mt-1 text-xl font-medium capitalize text-gray-950">{billing?.plan ?? "Loading"}</h2>
        {billing ? (
          <p className="mt-2 text-sm text-gray-600">
            Reports used this month: {billing.reports_limit === null ? "unlimited" : `${billing.reports_used_this_month} of ${billing.reports_limit}`}
            {" · "}Renews {formatDate(billing.period_reset_at)}
          </p>
        ) : null}
      </section>

      <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
        {plans.map((plan) => {
          const current = billing?.plan.toLowerCase() === plan.name.toLowerCase();
          return (
            <section key={plan.name} className={`rounded-lg border bg-white p-5 shadow-card ${plan.name === "Growth" ? "border-brand" : "border-gray-200"}`}>
              <h2 className="text-lg font-medium text-gray-950">{plan.name}</h2>
              <div className="mt-2 text-2xl font-bold text-gray-950">{plan.price}</div>
              <ul className="mt-4 space-y-2 text-sm text-gray-600">
                {plan.features.map((feature) => (
                  <li key={feature}>{feature}</li>
                ))}
              </ul>
              <Button className="mt-5 w-full" disabled={current} variant={current ? "secondary" : "primary"}>
                {current ? "Current plan" : "Upgrade"}
              </Button>
            </section>
          );
        })}
      </div>

      <section className="mt-6 rounded-lg border border-gray-200 bg-gray-50 p-5">
        <h2 className="text-base font-medium text-gray-950">Need just one more report?</h2>
        <p className="mt-1 text-sm text-gray-600">₹49 per additional report. Payment integration is ready for the next billing pass.</p>
        <Button className="mt-4" variant="secondary">
          Buy 1 report
        </Button>
      </section>
    </section>
  );
}
