import { Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { RiskBadge } from "../components/RiskBadge";
import { api } from "../lib/api";
import { formatCurrency, formatDate } from "../lib/format";
import type { ApplicantSummary } from "../types";

const tabs = [
  { label: "All", value: "" },
  { label: "Submitted", value: "submitted" },
  { label: "Skipped", value: "skipped" },
  { label: "Outcome pending", value: "pending" },
];

export function DashboardPage(): JSX.Element {
  const navigate = useNavigate();
  const [items, setItems] = useState<ApplicantSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");

  const params = useMemo(() => {
    const next = new URLSearchParams({ page: "1", limit: "20" });
    if (status) {
      next.set("status", status);
    }
    if (search.trim()) {
      next.set("search", search.trim());
    }
    return next;
  }, [search, status]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .listApplicants(params)
      .then((data) => {
        if (!cancelled) {
          setItems(data.items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [params]);

  return (
    <section className="min-h-[calc(100vh-56px)]">
      <div className="sticky top-14 z-20 flex items-center justify-between border-b border-gray-200 bg-white/95 px-4 py-4 backdrop-blur md:px-8">
        <h1 className="text-[28px] font-medium tracking-normal text-gray-950">Applicants</h1>
        <Link to="/screen">
          <Button>
            <Plus className="h-4 w-4" />
            <span className="hidden sm:inline">Screen new applicant</span>
            <span className="sm:hidden">New</span>
          </Button>
        </Link>
      </div>

      <div className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-6 md:flex-row md:items-center md:justify-between md:px-8">
        <div className="flex gap-2 overflow-x-auto">
          {tabs.map((tab) => (
            <button
              key={tab.label}
              className={`h-9 whitespace-nowrap rounded-full border px-4 text-sm font-medium ${
                status === tab.value ? "border-brand bg-indigo-50 text-brand" : "border-gray-200 text-gray-500 hover:bg-gray-50"
              }`}
              type="button"
              onClick={() => setStatus(tab.value)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <label className="relative block w-full md:w-[300px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            className="h-11 w-full rounded-lg border border-gray-200 pl-9 pr-3 outline-none focus:border-brand focus:ring-4 focus:ring-indigo-100"
            placeholder="Search by name or ID"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </div>

      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-4 pb-24 md:px-8">
        {loading ? (
          Array.from({ length: 3 }).map((_, index) => <div key={index} className="h-28 animate-pulse rounded-lg bg-gray-100" />)
        ) : items.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 p-10 text-center">
            <p className="text-gray-600">No applicants yet. Screen your first applicant to get started.</p>
            <Link className="mt-4 inline-flex" to="/screen">
              <Button>Screen new applicant</Button>
            </Link>
          </div>
        ) : (
          items.map((applicant) => (
            <button
              key={applicant.id}
              className="rounded-lg border border-gray-200 bg-white p-5 text-left shadow-card transition hover:border-gray-300"
              type="button"
              onClick={() => navigate(`/applicants/${applicant.id}`)}
            >
              <div className="flex items-start justify-between gap-4">
                <RiskBadge level={applicant.risk_class} />
                <div className="text-right text-sm text-gray-500">Score: {applicant.risk_score.toFixed(2)}</div>
              </div>
              <div className="mt-4 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-lg font-medium text-gray-950">{applicant.full_name || applicant.id.slice(0, 8)}</h2>
                  <p className="mt-1 text-sm text-gray-500">
                    Income {formatCurrency(applicant.income)} · Credit {formatCurrency(applicant.credit_amount)}
                  </p>
                </div>
                <div className="text-sm text-gray-500">
                  <div>{applicant.status}</div>
                  <div>{formatDate(applicant.created_at)}</div>
                </div>
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
}
