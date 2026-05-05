import { ArrowLeft } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { Button } from "../components/Button";
import { DecisionCard } from "../components/DecisionCard";
import { Modal } from "../components/Modal";
import { useToast } from "../contexts/ToastContext";
import { api } from "../lib/api";
import type { ApplicantDetail, CoachingTip, LenderOutcome } from "../types";

function reportString(report: Record<string, unknown> | null | undefined, key: string): string {
  const value = report?.[key];
  return typeof value === "string" ? value : "";
}

function reportDecision(report: Record<string, unknown> | null | undefined): { action: string; justification: string } {
  const decision = report?.decision;
  if (decision && typeof decision === "object" && "action" in decision) {
    const data = decision as { action?: unknown; justification?: unknown };
    return {
      action: typeof data.action === "string" ? data.action : "MANUAL REVIEW",
      justification: typeof data.justification === "string" ? data.justification : "",
    };
  }
  return { action: "MANUAL REVIEW", justification: "" };
}

function reportList(report: Record<string, unknown> | null | undefined, key: string): string[] {
  const value = report?.[key];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

export function ApplicantDetailPage(): JSX.Element {
  const { id } = useParams();
  const { notify } = useToast();
  const [applicant, setApplicant] = useState<ApplicantDetail | null>(null);
  const [coaching, setCoaching] = useState<CoachingTip[]>([]);
  const [loading, setLoading] = useState(true);
  const [decisionLoading, setDecisionLoading] = useState(false);
  const [showOverride, setShowOverride] = useState(false);

  useEffect(() => {
    if (!id) {
      return undefined;
    }
    let cancelled = false;
    setLoading(true);
    api
      .getApplicant(id)
      .then((data) => {
        if (!cancelled) {
          setApplicant(data);
          if (data.risk_class !== "Low") {
            void api.coaching(data.id).then((result) => {
              if (!cancelled) {
                setCoaching(result.tips);
              }
            });
          }
        }
      })
      .catch((error) => notify(error instanceof Error ? error.message : "Unable to load applicant."))
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [id, notify]);

  async function saveDecision(decision: "submitted" | "skipped"): Promise<void> {
    if (!applicant) {
      return;
    }
    if (decision === "submitted" && applicant.risk_class === "High") {
      setShowOverride(true);
      return;
    }
    setDecisionLoading(true);
    try {
      setApplicant({ ...applicant, dsa_decision: decision, status: decision === "submitted" ? "Submitted - pending" : "Not submitted" });
      const updated = await api.updateDecision(applicant.id, decision);
      setApplicant(updated);
      notify("Decision saved.", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to save decision.");
    } finally {
      setDecisionLoading(false);
    }
  }

  async function confirmOverride(): Promise<void> {
    if (!applicant) {
      return;
    }
    setShowOverride(false);
    setDecisionLoading(true);
    try {
      setApplicant({ ...applicant, dsa_decision: "submitted_override", status: "Submitted - pending" });
      const updated = await api.updateDecision(applicant.id, "submitted_override");
      setApplicant(updated);
      notify("Override submitted.", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to save override.");
    } finally {
      setDecisionLoading(false);
    }
  }

  async function saveOutcome(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!applicant) {
      return;
    }
    const data = new FormData(event.currentTarget);
    const lenderOutcome = String(data.get("lender_outcome")) as LenderOutcome;
    try {
      const updated = await api.updateOutcome(applicant.id, {
        lender_outcome: lenderOutcome,
        lender_name: String(data.get("lender_name") || ""),
      });
      setApplicant(updated);
      notify("Outcome saved.", "success");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to save outcome.");
    }
  }

  if (loading) {
    return <div className="p-8 text-gray-500">Loading applicant...</div>;
  }

  if (!applicant) {
    return <div className="p-8 text-gray-500">Applicant not found.</div>;
  }

  const decision = reportDecision(applicant.final_report);
  const decisionClass =
    decision.action === "REJECT"
      ? "border-risk-highBorder bg-risk-highBg text-risk-highText"
      : decision.action === "APPROVE"
        ? "border-risk-lowBorder bg-risk-lowBg text-risk-lowText"
        : "border-risk-uncertainBorder bg-risk-uncertainBg text-risk-uncertainText";

  return (
    <section className="mx-auto max-w-7xl px-4 py-6 pb-24 md:px-8">
      <header className="mb-6 flex items-start gap-4">
        <div>
          <Link className="mb-2 inline-flex items-center gap-2 text-sm text-gray-500 hover:text-brand" to="/dashboard">
            <ArrowLeft className="h-4 w-4" />
            Back to applicants
          </Link>
          <h1 className="text-[28px] font-medium tracking-normal text-gray-950">{applicant.full_name || "Applicant report"}</h1>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="space-y-6 lg:col-span-5">
          <DecisionCard
            applicant={applicant}
            submitLoading={decisionLoading}
            onSubmit={() => {
              if (applicant.risk_class === "High") {
                setShowOverride(true);
              } else {
                void saveDecision("submitted");
              }
            }}
            onSkip={() => void saveDecision("skipped")}
          />
        </div>

        <div className="space-y-5 lg:col-span-7">
          <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-card">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-base font-medium text-gray-950">AI Lending Report</h2>
              <span className="text-xs text-gray-500">Generated now</span>
            </div>
            <div className="rounded-lg bg-gray-50 p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.06em] text-gray-400">Applicant profile</div>
              <p className="text-sm leading-6 text-gray-700">{reportString(applicant.final_report, "profile") || "Profile unavailable."}</p>
            </div>
            <div className="mt-4 rounded-lg border border-gray-200 p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.06em] text-gray-400">Risk analysis</div>
              <p className="text-sm leading-6 text-gray-700">{reportString(applicant.final_report, "risk_analysis") || "Risk analysis unavailable."}</p>
            </div>
            <div className={`mt-4 rounded-lg border p-5 ${decisionClass}`}>
              <div className="text-xs font-semibold uppercase tracking-[0.06em]">Decision</div>
              <div className="mt-1 text-2xl font-bold">{decision.action}</div>
              <p className="mt-2 text-sm leading-6">{decision.justification || "Review the model score and applicant context before final submission."}</p>
            </div>
            <div className="mt-4 rounded-lg border border-gray-200 p-4">
              <div className="mb-2 text-xs font-semibold uppercase tracking-[0.06em] text-gray-400">Regulatory notes</div>
              <ul className="space-y-2 text-sm leading-6 text-gray-700">
                {reportList(applicant.final_report, "regulatory_summary").map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <p className="mt-4 text-xs italic text-gray-500">
              {reportString(applicant.final_report, "disclaimer") || "AI-assisted recommendation. Not the sole basis for lending decisions."}
            </p>
          </section>
        </div>
      </div>

      <Modal open={showOverride} title="Submit high-risk applicant?" onClose={() => setShowOverride(false)}>
        <p className="text-sm leading-6 text-gray-600">This applicant scored High risk. Submitting will be logged as an override for future model feedback.</p>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="secondary" type="button" onClick={() => setShowOverride(false)}>
            Cancel
          </Button>
          <Button type="button" onClick={() => void confirmOverride()}>
            Submit anyway
          </Button>
        </div>
      </Modal>
    </section>
  );
}
