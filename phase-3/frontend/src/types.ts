export type RiskClass = "Low" | "Uncertain" | "High";
export type Decision = "submitted" | "skipped" | "submitted_override";
export type LenderOutcome = "approved" | "rejected_credit" | "rejected_other";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
}

export interface FeatureImpact {
  feature: string;
  shap_value: number;
  direction: string;
}

export interface ScreeningPayload {
  full_name?: string;
  income: number;
  credit_amount: number;
  annuity: number;
  employment_years: number;
  age_years: number;
  family_size: number;
  education: string;
  income_type: string;
  housing_type: string;
  occupation?: string;
  family_status: string;
}

export interface ApplicantSummary {
  id: string;
  created_at: string;
  full_name: string | null;
  income: number;
  credit_amount: number;
  risk_score: number;
  risk_class: RiskClass | string;
  dsa_decision: Decision | null;
  lender_outcome: LenderOutcome | null;
  status: string;
}

export interface ApplicantDetail extends ApplicantSummary {
  annuity: number;
  employment_years: number;
  age_years: number;
  family_size: number;
  education: string;
  income_type: string;
  housing_type: string;
  occupation: string | null;
  family_status: string;
  confidence: number;
  model_version: string;
  shap_top_features: FeatureImpact[];
  feature_payload: Record<string, unknown>;
  final_report: Record<string, unknown> | null;
  processing_steps: string[];
  error_flags: string[];
  lender_name: string | null;
  outcome_logged_at: string | null;
  include_in_training: boolean;
}

export interface ApplicantList {
  items: ApplicantSummary[];
  page: number;
  limit: number;
  total: number;
}

export interface BillingStatus {
  plan: string;
  reports_used_this_month: number;
  reports_limit: number | null;
  reports_remaining: number | null;
  period_reset_at: string;
}

export interface CoachingTip {
  feature: string;
  current_value: number;
  suggested_value: number;
  score_improvement: number;
  human_tip: string;
}

export interface CoachingResponse {
  tips: CoachingTip[];
  current_score: number;
  best_achievable_score: number;
}
