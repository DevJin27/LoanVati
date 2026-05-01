import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { InputField } from "../components/FormField";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

export function LoginPage(): JSX.Element {
  const { login } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setLoading(true);
    try {
      await login(String(data.get("email")), String(data.get("password")));
      navigate("/dashboard", { replace: true });
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <section className="w-full max-w-[400px]">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-black tracking-tight text-brand">LoanVati</h1>
          <p className="mt-2 text-sm text-gray-500">Pre-screen before you submit.</p>
        </div>
        <form className="space-y-5 rounded-lg border border-gray-200 bg-white p-6 shadow-card" onSubmit={handleSubmit}>
          <InputField label="Email" name="email" type="email" placeholder="agent@dsa.com" required />
          <InputField label="Password" name="password" type="password" placeholder="Password" required />
          <Button className="w-full" loading={loading} type="submit">
            Sign in
          </Button>
          <p className="border-t border-gray-100 pt-4 text-center text-sm text-gray-500">
            No account?{" "}
            <Link className="font-medium text-brand hover:text-brand-hover" to="/register">
              Register
            </Link>
          </p>
        </form>
      </section>
    </main>
  );
}
