/**
 * DecisionCard
 *
 * A self-contained loan decision card.
 * Surfaces the outcome, confidence, and reasoning
 * in plain language — no ML jargon exposed to the user.
 */

import { ChevronDown, ChevronUp, MessageSquare, ShieldAlert, ShieldCheck, ShieldQuestion, Star } from "lucide-react";
import { useState } from "react";

import type { ApplicantDetail, FeatureImpact } from "../types";
import { formatCurrency, formatDate } from "../lib/format";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DecisionCardProps {
  applicant: ApplicantDetail;
  onSubmit: () => void;
  onSkip: () => void;
  submitLoading?: boolean;
}

type FeedbackRating = 1 | 2 | 3 | 4 | 5;

interface DsaFeedback {
  rating: FeedbackRating | null;
  note: string;
  submittedAt: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function isGuardrailDecision(modelVersion: string): boolean {
  return modelVersion.includes("guardrail");
}

function normalizeRiskClass(raw: string): "Low" | "Uncertain" | "High" {
  if (raw.includes("High")) return "High";
  if (raw.includes("Uncertain") || raw.includes("Manual")) return "Uncertain";
  return "Low";
}

function decisionFromReport(report: Record<string, unknown> | null | undefined): {
  action: string;
  justification: string;
} {
  const d = report?.decision;
  if (d && typeof d === "object" && "action" in d) {
    const t = d as { action?: unknown; justification?: unknown };
    return {
      action: typeof t.action === "string" ? t.action : "MANUAL REVIEW",
      justification: typeof t.justification === "string" ? t.justification : "",
    };
  }
  return { action: "MANUAL REVIEW", justification: "" };
}

function confidenceLabel(confidence: number): "High" | "Medium" | "Low" {
  if (confidence >= 0.70) return "High";
  if (confidence >= 0.35) return "Medium";
  return "Low";
}

/** Convert a raw feature impact into plain-language text. */
function featureToPlain(f: FeatureImpact): { label: string; detail: string } {
  const PLAIN: Record<string, { label: string; detail: (dir: string) => string }> = {
    "Annual Income": {
      label: "Repayment burden",
      detail: (d) =>
        d === "increases risk"
          ? "The loan burden is high relative to income — higher repayments reduce ability to service debt"
          : "Income comfortably covers the repayment — low burden relative to earnings",
    },
    "Income Per Person": {
      // INCOME_PER_PERSON is a training artefact that should be removed on retrain.
      // Show a safe label in the meantime rather than exposing the raw feature name.
      label: "Household income adequacy",
      detail: (d) =>
        d === "increases risk"
          ? "Income per household member is lower, reducing financial buffer"
          : "Household income per member is sufficient to absorb repayments",
    },
    "Credit Amount": {
      label: "Loan size",
      detail: (d) =>
        d === "increases risk"
          ? "The loan amount is high relative to income"
          : "The loan amount is manageable relative to income",
    },
    "Annual Annuity": {
      label: "Monthly repayment",
      detail: (d) =>
        d === "increases risk"
          ? "EMI is a large share of monthly income"
          : "EMI is comfortably within monthly income",
    },
    "Employment Duration": {
      label: "Employment stability",
      detail: (d) =>
        d === "increases risk"
          ? "Short employment history increases uncertainty"
          : "Long employment history reduces uncertainty",
    },
    "Applicant Age": {
      label: "Applicant profile",
      detail: (d) =>
        d === "increases risk"
          ? "Age profile is associated with higher default rates"
          : "Age profile is associated with lower default rates",
    },
    "External Credit Score 1": {
      label: "Bureau score 1",
      detail: (d) =>
        d === "increases risk" ? "Bureau score is below average" : "Bureau score is above average",
    },
    "External Credit Score 2": {
      label: "Bureau score 2",
      detail: (d) =>
        d === "increases risk" ? "Credit history shows concern" : "Credit history is positive",
    },
    "External Credit Score 3": {
      label: "Bureau score 3",
      detail: (d) =>
        d === "increases risk" ? "Alternative score is low" : "Alternative score is strong",
    },
  };

  const baseName = Object.keys(PLAIN).find((k) => f.feature.startsWith(k));
  if (baseName) {
    return {
      label: PLAIN[baseName].label,
      detail: PLAIN[baseName].detail(f.direction),
    };
  }

  return {
    label: f.feature.replace(/_/g, " "),
    detail:
      f.direction === "increases risk"
        ? "This factor is elevating the assessed risk"
        : "This factor is reducing the assessed risk",
  };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function RiskIcon({ level }: { level: "Low" | "Uncertain" | "High" }) {
  if (level === "Low")
    return <ShieldCheck className="h-4 w-4 text-risk-lowText" aria-hidden />;
  if (level === "High")
    return <ShieldAlert className="h-4 w-4 text-risk-highText" aria-hidden />;
  return <ShieldQuestion className="h-4 w-4 text-risk-uncertainText" aria-hidden />;
}

function RiskBand({ level }: { level: "Low" | "Uncertain" | "High" }) {
  const cls =
    level === "High"
      ? "border-risk-highBorder bg-risk-highBg text-risk-highText"
      : level === "Uncertain"
        ? "border-risk-uncertainBorder bg-risk-uncertainBg text-risk-uncertainText"
        : "border-risk-lowBorder bg-risk-lowBg text-risk-lowText";
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wide ${cls}`}
    >
      <RiskIcon level={level} />
      {level === "Uncertain" ? "Manual Review" : level + " Risk"}
    </span>
  );
}

/**
 * KpiBox — centered tile with a label on top and a large value below.
 * Fix: added text-center + items-center so both label and value align.
 */
function KpiBox({
  label,
  value,
  sub,
  highlight,
}: {
  label: string;
  value: string;
  sub?: string;
  highlight?: "low" | "uncertain" | "high";
}) {
  const valueClass =
    highlight === "high"
      ? "text-risk-highText"
      : highlight === "uncertain"
        ? "text-risk-uncertainText"
        : highlight === "low"
          ? "text-risk-lowText"
          : "text-gray-950";

  return (
    <div className="flex flex-col items-center gap-1.5 rounded-lg border border-gray-100 bg-gray-50 px-4 py-5 text-center">
      <dt className="text-[10px] font-semibold uppercase tracking-widest text-gray-400">{label}</dt>
      <dd className={`text-2xl font-bold leading-none tabular-nums ${valueClass}`}>{value}</dd>
      {sub && <span className="text-[11px] leading-tight text-gray-500">{sub}</span>}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-3 text-[10px] font-bold uppercase tracking-widest text-gray-400">
      {children}
    </div>
  );
}

function Divider() {
  return <hr className="my-5 border-gray-100" />;
}

/** Star rating row for the DSA feedback panel. */
function StarRow({
  value,
  onChange,
}: {
  value: FeedbackRating | null;
  onChange: (v: FeedbackRating) => void;
}) {
  return (
    <div className="flex gap-1" role="group" aria-label="Rating">
      {([1, 2, 3, 4, 5] as FeedbackRating[]).map((n) => (
        <button
          key={n}
          type="button"
          id={`btn-feedback-star-${n}`}
          onClick={() => onChange(n)}
          className={`transition-colors ${
            value !== null && n <= value ? "text-amber-400" : "text-gray-300 hover:text-amber-300"
          }`}
          aria-label={`${n} star${n > 1 ? "s" : ""}`}
        >
          <Star className="h-5 w-5 fill-current" />
        </button>
      ))}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function DecisionCard({
  applicant,
  onSubmit,
  onSkip,
  submitLoading = false,
}: DecisionCardProps): JSX.Element {
  const [auditOpen, setAuditOpen] = useState(false);
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackRating, setFeedbackRating] = useState<FeedbackRating | null>(null);
  const [feedbackNote, setFeedbackNote] = useState("");
  const [feedback, setFeedback] = useState<DsaFeedback | null>(null);

  const riskLevel = normalizeRiskClass(applicant.risk_class);
  const isGuardrail = isGuardrailDecision(applicant.model_version);
  const { action: decisionAction, justification } = decisionFromReport(applicant.final_report);
  const confLabel = confidenceLabel(applicant.confidence);
  const decisionType = isGuardrail ? "Rule-based" : "Model-based";

  const defaultPercent = Math.round(applicant.risk_score * 100);

  const fp = applicant.feature_payload as Record<string, number>;
  const dti = typeof fp.CREDIT_INCOME_RATIO === "number" ? fp.CREDIT_INCOME_RATIO : null;
  const pti = typeof fp.ANNUITY_INCOME_RATIO === "number" ? fp.ANNUITY_INCOME_RATIO : null;
  const employedPerc = typeof fp.DAYS_EMPLOYED_PERC === "number" ? fp.DAYS_EMPLOYED_PERC : null;

  const triggeredRule = (() => {
    if (!isGuardrail) return null;
    if (applicant.risk_score <= 0.10) return "Debt and payment ratios are extremely low";
    if (applicant.risk_score >= 0.90) {
      if (!fp.AMT_INCOME_TOTAL || fp.AMT_INCOME_TOTAL <= 0) return "Income is missing or zero";
      if (dti !== null && dti > 20) return "Loan amount exceeds 20× annual income";
      if (pti !== null && pti > 0.80) return "Monthly payment exceeds 80% of monthly income";
      return "Financial ratios are outside acceptable limits";
    }
    if (fp.AMT_INCOME_TOTAL > 1e8) return "Income is above the system's reliable assessment range";
    return "An automatic rule was applied";
  })();

  const decisionHighlight: "low" | "uncertain" | "high" =
    decisionAction === "APPROVE" ? "low" : decisionAction === "REJECT" ? "high" : "uncertain";

  const alreadyDecided = Boolean(applicant.dsa_decision);

  function submitFeedback() {
    if (!feedbackRating) return;
    setFeedback({
      rating: feedbackRating,
      note: feedbackNote.trim(),
      submittedAt: new Date().toLocaleString("en-IN", { hour12: true }),
    });
    setFeedbackOpen(false);
  }

  return (
    <article className="rounded-xl border border-gray-200 bg-white shadow-card">

      {/* ── Header ── */}
      <header className="flex items-start justify-between gap-4 border-b border-gray-100 px-6 py-5">
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
            Applicant report
          </p>
          <h2 className="mt-1 truncate text-lg font-semibold leading-snug text-gray-950">
            {applicant.full_name || "Unnamed applicant"}
          </h2>
        </div>
        <RiskBand level={riskLevel} />
      </header>

      <div className="px-6 py-5">

        {/* ── Primary KPIs ── */}
        <SectionLabel>Summary</SectionLabel>
        <dl className="grid grid-cols-3 gap-3">
          <KpiBox
            label="Risk of default"
            value={`${defaultPercent}%`}
            sub={
              riskLevel === "Low"
                ? "Below threshold"
                : riskLevel === "High"
                  ? "Above threshold"
                  : "Near threshold"
            }
            highlight={
              riskLevel === "High" ? "high" : riskLevel === "Uncertain" ? "uncertain" : "low"
            }
          />
          <KpiBox
            label="Recommendation"
            value={decisionAction}
            highlight={decisionHighlight}
          />
          <KpiBox
            label="Confidence"
            value={confLabel}
            sub={decisionType}
          />
        </dl>

        <Divider />

        {/* ── Decision Context ── */}
        <SectionLabel>Financial snapshot</SectionLabel>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
          <div>
            <dt className="text-xs font-medium text-gray-400">Annual income</dt>
            <dd className="mt-0.5 text-base font-semibold text-gray-900">
              {formatCurrency(applicant.income)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-gray-400">Loan requested</dt>
            <dd className="mt-0.5 text-base font-semibold text-gray-900">
              {formatCurrency(applicant.credit_amount)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-gray-400">Monthly repayment</dt>
            <dd className="mt-0.5 text-base font-semibold text-gray-900">
              {formatCurrency(applicant.annuity / 12)}
            </dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-gray-400">Decision source</dt>
            <dd className="mt-0.5 text-base font-semibold text-gray-900">{decisionType}</dd>
          </div>
        </dl>

        <Divider />

        {/* ── Why this decision? ── */}
        <SectionLabel>Why this decision?</SectionLabel>

        {justification && (
          <p className="mb-4 text-sm leading-relaxed text-gray-700">{justification}</p>
        )}

        {/* Rule-based path */}
        {isGuardrail ? (
          <div className="space-y-3">
            {triggeredRule && (
              <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                <p className="text-sm leading-relaxed text-gray-700">
                  <span className="font-semibold text-gray-900">Rule triggered: </span>
                  {triggeredRule}
                </p>
              </div>
            )}
            <div className="grid grid-cols-3 gap-3">
              {dti !== null && (
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
                  <div className="text-xl font-bold tabular-nums text-gray-950">
                    {dti.toFixed(2)}×
                  </div>
                  <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-gray-400">
                    Debt to income
                  </div>
                </div>
              )}
              {pti !== null && (
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
                  <div className="text-xl font-bold tabular-nums text-gray-950">
                    {Math.round(pti * 100)}%
                  </div>
                  <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-gray-400">
                    Payment to income
                  </div>
                </div>
              )}
              {employedPerc !== null && (
                <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
                  <div className="text-xl font-bold tabular-nums text-gray-950">
                    {Math.round(Math.abs(employedPerc) * 100)}%
                  </div>
                  <div className="mt-1 text-[11px] font-medium uppercase tracking-wide text-gray-400">
                    Employment
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Model-based path */
          applicant.shap_top_features.length > 0 ? (
            <ul className="space-y-3">
              {applicant.shap_top_features.slice(0, 4).map((f) => {
                const { label, detail } = featureToPlain(f);
                const positive = f.shap_value >= 0;
                return (
                  <li
                    key={`${f.feature}-${f.shap_value}`}
                    className="flex items-start gap-3"
                  >
                    <span
                      className={`mt-[5px] h-2 w-2 shrink-0 rounded-full ${positive ? "bg-risk-highBorder" : "bg-risk-lowBorder"}`}
                      aria-hidden
                    />
                    <p className="text-sm leading-relaxed">
                      <span className="font-semibold text-gray-900">{label}</span>
                      <span className="text-gray-600"> — {detail}</span>
                    </p>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="text-sm text-gray-500">Explanation data unavailable.</p>
          )
        )}

        <Divider />

        {/* ── Actions ── */}
        {!alreadyDecided ? (
          <div className="flex gap-3">
            <button
              id="btn-submit-to-lender"
              type="button"
              disabled={submitLoading}
              onClick={onSubmit}
              className="flex-1 rounded-lg bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-hover disabled:opacity-50"
            >
              {submitLoading ? "Submitting…" : "Submit to lender"}
            </button>
            <button
              id="btn-skip-applicant"
              type="button"
              disabled={submitLoading}
              onClick={onSkip}
              className="flex-1 rounded-lg border border-gray-200 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Skip applicant
            </button>
          </div>
        ) : (
          <p className="text-sm text-gray-600">
            Status:{" "}
            <span className="font-semibold text-gray-950">{applicant.status}</span>
          </p>
        )}

        <Divider />

        {/* ── DSA Feedback ── */}
        <div>
          {feedback ? (
            /* Submitted state */
            <div className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-widest text-gray-400">
                  Your feedback
                </span>
                <button
                  id="btn-feedback-edit"
                  type="button"
                  className="text-xs text-brand hover:underline"
                  onClick={() => {
                    setFeedback(null);
                    setFeedbackOpen(true);
                  }}
                >
                  Edit
                </button>
              </div>
              <div className="mt-2 flex gap-0.5">
                {([1, 2, 3, 4, 5] as FeedbackRating[]).map((n) => (
                  <Star
                    key={n}
                    className={`h-4 w-4 fill-current ${
                      feedback.rating !== null && n <= feedback.rating
                        ? "text-amber-400"
                        : "text-gray-200"
                    }`}
                  />
                ))}
              </div>
              {feedback.note && (
                <p className="mt-2 text-sm leading-relaxed text-gray-700">"{feedback.note}"</p>
              )}
              <p className="mt-1 text-[11px] text-gray-400">Submitted {feedback.submittedAt}</p>
            </div>
          ) : feedbackOpen ? (
            /* Input state */
            <div className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-4">
              <p className="mb-3 text-sm font-semibold text-gray-900">
                How accurate was this report?
              </p>
              <StarRow value={feedbackRating} onChange={setFeedbackRating} />
              <textarea
                id="feedback-note"
                rows={3}
                value={feedbackNote}
                onChange={(e) => setFeedbackNote(e.target.value)}
                placeholder="Optional note — e.g. 'Risk score seems too high for this income profile'"
                className="mt-3 w-full resize-none rounded-lg border border-gray-200 bg-white px-3.5 py-2.5 text-sm leading-relaxed text-gray-900 placeholder:text-gray-400 outline-none focus:border-brand focus:ring-4 focus:ring-indigo-100"
              />
              <div className="mt-3 flex gap-2">
                <button
                  id="btn-feedback-submit"
                  type="button"
                  disabled={!feedbackRating}
                  onClick={submitFeedback}
                  className="rounded-lg bg-brand px-4 py-2 text-xs font-semibold text-white hover:bg-brand-hover disabled:opacity-40"
                >
                  Submit feedback
                </button>
                <button
                  id="btn-feedback-cancel"
                  type="button"
                  onClick={() => setFeedbackOpen(false)}
                  className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-100"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            /* Trigger button */
            <button
              id="btn-feedback-open"
              type="button"
              onClick={() => setFeedbackOpen(true)}
              className="flex items-center gap-2 text-xs font-medium text-gray-400 hover:text-gray-600"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              Leave feedback on this report
            </button>
          )}
        </div>

        {/* ── Audit / Trace (collapsed) ── */}
        <div className="mt-5">
          <button
            type="button"
            className="flex w-full items-center justify-between text-xs font-medium text-gray-400 hover:text-gray-600"
            onClick={() => setAuditOpen((o) => !o)}
            aria-expanded={auditOpen}
            id="btn-audit-toggle"
          >
            <span>Audit trace</span>
            {auditOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>

          {auditOpen && (
            <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-3 rounded-lg border border-gray-100 bg-gray-50 p-4 text-xs">
              <div>
                <dt className="font-medium text-gray-400">Decision source</dt>
                <dd className="mt-0.5 font-semibold text-gray-700">{decisionType}</dd>
              </div>
              <div>
                <dt className="font-medium text-gray-400">Model version</dt>
                <dd className="mt-0.5 font-semibold text-gray-700">{applicant.model_version}</dd>
              </div>
              {triggeredRule && (
                <div className="col-span-2">
                  <dt className="font-medium text-gray-400">Triggered rule</dt>
                  <dd className="mt-0.5 font-semibold text-gray-700">{triggeredRule}</dd>
                </div>
              )}
              <div>
                <dt className="font-medium text-gray-400">Report generated</dt>
                <dd className="mt-0.5 font-semibold text-gray-700">
                  {formatDate(applicant.created_at)}
                </dd>
              </div>
              <div>
                <dt className="font-medium text-gray-400">Trace ID</dt>
                <dd className="mt-0.5 font-mono font-semibold text-gray-700">
                  {applicant.id.slice(0, 8).toUpperCase()}
                </dd>
              </div>
              {applicant.error_flags.length > 0 && (
                <div className="col-span-2">
                  <dt className="font-medium text-gray-400">Flags</dt>
                  <dd className="mt-0.5 font-semibold text-risk-highText">
                    {applicant.error_flags.join(", ")}
                  </dd>
                </div>
              )}
            </dl>
          )}
        </div>
      </div>
    </article>
  );
}
