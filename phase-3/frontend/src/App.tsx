import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "./components/Layout";
import { useAuth } from "./contexts/AuthContext";
import { ApplicantDetailPage } from "./pages/ApplicantDetailPage";
import { BillingPage } from "./pages/BillingPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { ScreenPage } from "./pages/ScreenPage";
import { SettingsPage } from "./pages/SettingsPage";

function ProtectedRoutes(): JSX.Element {
  const { authenticated, loading } = useAuth();
  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-gray-500">Loading LoanVati...</div>;
  }
  if (!authenticated) {
    return <Navigate replace to="/login" />;
  }
  return <Layout />;
}

export function App(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoutes />}>
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/screen" element={<ScreenPage />} />
        <Route path="/applicants/:id" element={<ApplicantDetailPage />} />
        <Route path="/billing" element={<BillingPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
