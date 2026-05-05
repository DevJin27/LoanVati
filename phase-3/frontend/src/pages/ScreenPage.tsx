import { ArrowLeft } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { CurrencyField, InputField, SelectField } from "../components/FormField";
import { ProgressSteps } from "../components/ProgressSteps";
import { useToast } from "../contexts/ToastContext";
import { api } from "../lib/api";
import type { ScreeningPayload } from "../types";

const educationOptions = [
  "Secondary / secondary special",
  "Higher secondary",
  "Higher education",
  "Academic degree",
  "Lower secondary",
  "Incomplete higher",
];
const incomeTypeOptions = ["Working", "Commercial associate", "Pensioner", "State servant", "Unemployed", "Student", "Businessman", "Maternity leave"];
const housingOptions = ["House / apartment", "Rented apartment", "Municipal apartment", "With parents", "Co-op apartment", "Office apartment"];
const occupationOptions = ["Laborers", "Sales staff", "Core staff", "Managers", "Drivers", "Accountants", "High skill tech staff", "Medicine staff", "Other"];
const familyStatusOptions = ["Married", "Single / not married", "Civil marriage", "Separated", "Widow"];
const genderOptions = ["Prefer not to say", "Male (M)", "Female (F)", "Other / Not disclosed (XNA)"];
const progressSteps = ["Scoring applicant", "Running SHAP analysis", "Generating report"];

export function ScreenPage(): JSX.Element {
  const navigate = useNavigate();
  const { notify } = useToast();
  const [loading, setLoading] = useState(false);
  const [activeStep, setActiveStep] = useState(0);

  useEffect(() => {
    if (!loading) {
      setActiveStep(0);
      return undefined;
    }
    const interval = window.setInterval(() => {
      setActiveStep((step) => Math.min(step + 1, progressSteps.length - 1));
    }, 1000);
    return () => window.clearInterval(interval);
  }, [loading]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const payload: ScreeningPayload = {
      full_name: String(data.get("full_name") || ""),
      income: Number(data.get("income")),
      credit_amount: Number(data.get("credit_amount")),
      annuity: Number(data.get("annuity")),
      employment_years: Number(data.get("employment_years")),
      age_years: Number(data.get("age_years")),
      family_size: Number(data.get("family_size")),
      education: String(data.get("education")),
      income_type: String(data.get("income_type")),
      housing_type: String(data.get("housing_type")),
      occupation: String(data.get("occupation")),
      family_status: String(data.get("family_status")),
      gender: (() => {
        const raw = String(data.get("gender") || "");
        // Extract the code inside parentheses, e.g. "Male (M)" -> "M"
        const match = raw.match(/\(([^)]+)\)$/);
        return match ? match[1] : undefined;
      })(),
    };

    setLoading(true);
    try {
      const applicant = await api.screenApplicant(payload);
      navigate(`/applicants/${applicant.id}`);
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to screen applicant.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="min-h-[calc(100vh-56px)] bg-white pb-24 md:pb-10">
      <header className="sticky top-14 z-20 flex h-14 items-center gap-4 border-b border-gray-200 bg-white px-4 md:px-8">
        <Link className="rounded p-1 text-gray-500 hover:bg-gray-100" to="/dashboard" aria-label="Back to dashboard">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <h1 className="text-lg font-medium text-gray-950">Screen applicant</h1>
      </header>
      <form className="mx-auto max-w-3xl px-4 py-6 md:px-8" onSubmit={handleSubmit}>
        <section className="space-y-5">
          <div>
            <h2 className="text-xs font-semibold uppercase tracking-[0.06em] text-gray-400">Applicant details</h2>
            <div className="mt-4 grid grid-cols-1 gap-5 md:grid-cols-2">
              <InputField label="Full name" name="full_name" placeholder="Applicant name" />
              <CurrencyField label="Annual income" name="income" min={1} required />
              <CurrencyField label="Credit amount requested" name="credit_amount" min={1} required />
              <CurrencyField label="Loan annuity / EMI" name="annuity" min={1} required />
              <InputField label="Employment years" name="employment_years" type="number" min="0" step="0.1" required />
            </div>
          </div>

          <div className="pt-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.06em] text-gray-400">Demographics</h2>
            <div className="mt-4 grid grid-cols-1 gap-5 md:grid-cols-2">
              <InputField label="Age (years)" name="age_years" type="number" min="18" max="100" required />
              <InputField label="Family size" name="family_size" type="number" min="1" max="10" required />
              <SelectField label="Education level" name="education" options={educationOptions} />
              <SelectField label="Income type" name="income_type" options={incomeTypeOptions} />
              <SelectField label="Housing type" name="housing_type" options={housingOptions} />
              <SelectField label="Occupation type" name="occupation" options={occupationOptions} />
              <SelectField label="Family status" name="family_status" options={familyStatusOptions} />
              <SelectField label="Gender" name="gender" options={genderOptions} defaultValue="Prefer not to say" />
            </div>
          </div>
        </section>

        <div className="pb-safe fixed bottom-0 left-0 z-30 w-full border-t border-gray-200 bg-white p-4 md:static md:mt-8 md:border-0 md:p-0">
          <Button className="w-full" loading={loading} type="submit">
            Get risk score
          </Button>
        </div>
      </form>

      {loading ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-xl border border-gray-200 bg-white p-6 shadow-card">
            <h2 className="mb-5 text-lg font-medium text-gray-950">Processing application</h2>
            <ProgressSteps activeIndex={activeStep} steps={progressSteps} />
          </div>
        </div>
      ) : null}
    </section>
  );
}
