import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";

interface FieldShellProps {
  label: string;
  error?: string;
  children: ReactNode;
}

function FieldShell({ label, error, children }: FieldShellProps): JSX.Element {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium uppercase tracking-[0.06em] text-gray-500">{label}</span>
      {children}
      {error ? <span className="mt-1 block text-xs text-red-500">{error}</span> : null}
    </label>
  );
}

interface InputFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export function InputField({ label, error, className = "", ...props }: InputFieldProps): JSX.Element {
  return (
    <FieldShell label={label} error={error}>
      <input
        className={`h-11 w-full rounded-lg border px-3.5 text-[15px] outline-none transition focus:border-brand focus:ring-4 focus:ring-indigo-100 ${
          error ? "border-red-400" : "border-gray-200"
        } ${className}`}
        {...props}
      />
    </FieldShell>
  );
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  error?: string;
  options: string[];
}

export function SelectField({ label, error, options, className = "", ...props }: SelectFieldProps): JSX.Element {
  return (
    <FieldShell label={label} error={error}>
      <select
        className={`h-11 w-full rounded-lg border bg-white px-3.5 text-[15px] outline-none transition focus:border-brand focus:ring-4 focus:ring-indigo-100 ${
          error ? "border-red-400" : "border-gray-200"
        } ${className}`}
        {...props}
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}
