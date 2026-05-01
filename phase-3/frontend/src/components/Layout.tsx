import { CreditCard, Home, LogOut, Settings, UserSearch } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";

import { useAuth } from "../contexts/AuthContext";
import { api } from "../lib/api";
import type { BillingStatus } from "../types";

const navItems = [
  { to: "/dashboard", label: "Dashboard", icon: Home },
  { to: "/screen", label: "Screen", icon: UserSearch },
  { to: "/billing", label: "Billing", icon: CreditCard },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Layout(): JSX.Element {
  const { user, logout } = useAuth();
  const [billing, setBilling] = useState<BillingStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .billingStatus()
      .then((status) => {
        if (!cancelled) {
          setBilling(status);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  const quotaText = billing
    ? billing.reports_limit === null
      ? `${billing.plan} - unlimited`
      : `${billing.plan} - ${billing.reports_used_this_month} of ${billing.reports_limit} used`
    : "Plan loading";

  return (
    <div className="min-h-screen bg-white pb-14 md:pb-0">
      <aside className="fixed left-0 top-0 z-40 hidden h-full w-[220px] border-r border-gray-200 bg-white md:flex md:flex-col">
        <div className="px-4 py-6">
          <div className="text-xl font-black tracking-tight text-gray-950">LoanVati</div>
          <div className="mt-1 text-xs uppercase tracking-wide text-gray-500">{quotaText}</div>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-2">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-brand text-white" : "text-gray-600 hover:bg-gray-100"
                }`
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-200 p-4">
          <div className="text-sm font-medium text-gray-900">{user?.full_name ?? user?.email}</div>
          <button className="mt-2 flex items-center gap-2 text-sm text-gray-500 hover:text-brand" type="button" onClick={logout}>
            <LogOut className="h-4 w-4" />
            Sign out
          </button>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4 md:ml-[220px]">
        <div className="font-black tracking-tight text-gray-950 md:hidden">LoanVati</div>
        <div className="hidden md:block" />
        <div className="text-sm font-medium text-gray-600">{quotaText}</div>
      </header>

      <main className="md:ml-[220px]">
        <Outlet />
      </main>

      <nav className="pb-safe fixed bottom-0 left-0 z-40 grid h-14 w-full grid-cols-3 border-t border-gray-200 bg-white md:hidden">
        {navItems
          .filter((item) => item.to !== "/billing")
          .map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center gap-0.5 text-[11px] font-semibold ${
                  isActive ? "text-brand" : "text-gray-400"
                }`
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
      </nav>
    </div>
  );
}
