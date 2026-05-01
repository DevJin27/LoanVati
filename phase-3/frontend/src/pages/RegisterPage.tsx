import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Button } from "../components/Button";
import { InputField } from "../components/FormField";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

export function RegisterPage(): JSX.Element {
  const { register } = useAuth();
  const { notify } = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password"));
    const confirm = String(data.get("confirm"));
    if (password !== confirm) {
      setPasswordError("Passwords do not match.");
      return;
    }
    setPasswordError("");
    setLoading(true);
    try {
      await register(String(data.get("fullName")), String(data.get("email")), password);
      navigate("/dashboard", { replace: true });
    } catch (error) {
      notify(error instanceof Error ? error.message : "Unable to create account.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <section className="w-full max-w-[400px]">
        <div className="mb-8 text-center">
          <h1 className="text-3xl font-black tracking-tight text-brand">LoanVati</h1>
          <p className="mt-2 text-sm text-gray-500">Create your DSA workspace.</p>
        </div>
        <form className="space-y-5 rounded-lg border border-gray-200 bg-white p-6 shadow-card" onSubmit={handleSubmit}>
          <InputField label="Full name" name="fullName" required />
          <InputField label="Email" name="email" type="email" required />
          <InputField label="Password" name="password" type="password" required minLength={8} />
          <InputField label="Confirm password" name="confirm" type="password" required error={passwordError} />
          <Button className="w-full" loading={loading} type="submit">
            Create account
          </Button>
          <p className="border-t border-gray-100 pt-4 text-center text-sm text-gray-500">
            Already registered?{" "}
            <Link className="font-medium text-brand hover:text-brand-hover" to="/login">
              Sign in
            </Link>
          </p>
        </form>
      </section>
    </main>
  );
}
