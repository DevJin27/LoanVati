import type {
  ApplicantDetail,
  ApplicantList,
  BillingStatus,
  CoachingResponse,
  Decision,
  LenderOutcome,
  ScreeningPayload,
  User,
} from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(/\/$/, "");
const TOKEN_KEY = "loanvati_token";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit & { timeoutMs?: number } = {}): Promise<T> {
  const timeoutMs = options.timeoutMs ?? 15000;
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs);
  const token = getToken();

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    });

    if (response.status === 401) {
      clearToken();
      window.dispatchEvent(new CustomEvent("loanvati:unauthorized"));
    }

    if (!response.ok) {
      let message = "Something went wrong. Try again.";
      try {
        const body = (await response.json()) as { detail?: string };
        message = body.detail ?? message;
      } catch {
        // Keep the stable default.
      }
      throw new ApiError(message, response.status);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  } finally {
    window.clearTimeout(timeout);
  }
}

export const api = {
  async register(payload: { full_name: string; email: string; password: string }): Promise<void> {
    const result = await request<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(result.access_token);
  },
  async login(payload: { email: string; password: string }): Promise<void> {
    const result = await request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    setToken(result.access_token);
  },
  me: () => request<User>("/auth/me"),
  billingStatus: () => request<BillingStatus>("/billing/status"),
  listApplicants: (params: URLSearchParams) => request<ApplicantList>(`/applicants?${params.toString()}`),
  getApplicant: (id: string) => request<ApplicantDetail>(`/applicants/${id}`),
  screenApplicant: (payload: ScreeningPayload) =>
    request<ApplicantDetail>("/applicants/screen", {
      method: "POST",
      body: JSON.stringify(payload),
      timeoutMs: 30000,
    }),
  updateDecision: (id: string, decision: Decision) =>
    request<ApplicantDetail>(`/applicants/${id}/decision`, {
      method: "PATCH",
      body: JSON.stringify({ decision }),
    }),
  updateOutcome: (id: string, payload: { lender_outcome: LenderOutcome; lender_name?: string }) =>
    request<ApplicantDetail>(`/applicants/${id}/outcome`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  coaching: (applicantId: string) =>
    request<CoachingResponse>("/coaching", {
      method: "POST",
      body: JSON.stringify({ applicant_id: applicantId }),
    }),
};
