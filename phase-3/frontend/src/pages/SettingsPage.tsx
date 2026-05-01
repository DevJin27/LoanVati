import { FormEvent } from "react";

import { Button } from "../components/Button";
import { InputField } from "../components/FormField";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../contexts/ToastContext";

export function SettingsPage(): JSX.Element {
  const { user, logout } = useAuth();
  const { notify } = useToast();

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    notify("Profile settings are read-only in this MVP.", "success");
  }

  return (
    <section className="mx-auto max-w-4xl px-4 py-6 pb-24 md:px-8">
      <h1 className="text-[28px] font-medium tracking-normal text-gray-950">Settings</h1>
      <form className="mt-6 space-y-6" onSubmit={handleSubmit}>
        <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-card">
          <h2 className="mb-5 text-lg font-medium text-gray-950">Profile</h2>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <InputField label="Full name" name="full_name" defaultValue={user?.full_name ?? ""} />
            <InputField label="Email" name="email" value={user?.email ?? ""} readOnly />
          </div>
        </section>

        <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-card">
          <h2 className="mb-5 text-lg font-medium text-gray-950">Change password</h2>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
            <InputField label="Current password" type="password" />
            <InputField label="New password" type="password" />
            <InputField label="Confirm password" type="password" />
          </div>
        </section>

        <div className="flex justify-end">
          <Button type="submit">Save changes</Button>
        </div>
      </form>

      <section className="mt-8 rounded-lg border border-risk-highBorder bg-white p-6">
        <h2 className="text-lg font-medium text-risk-highText">Danger zone</h2>
        <p className="mt-1 text-sm text-gray-600">Account deletion is intentionally disabled in this MVP.</p>
        <Button className="mt-4" type="button" variant="destructive" onClick={logout}>
          Sign out
        </Button>
      </section>
    </section>
  );
}
