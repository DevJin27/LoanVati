import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { useState } from "react";

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

interface CurrencyFieldProps {
  label: string;
  name: string;
  required?: boolean;
  min?: number;
  error?: string;
  defaultValue?: number;
}

/**
 * CurrencyField
 *
 * Displays a ₹-prefixed text input with Indian-locale comma formatting
 * (e.g. ₹1,80,000) as the user types. A hidden `<input type="number">`
 * with the same `name` carries the raw numeric value so FormData picks
 * it up correctly — no parsing needed in handleSubmit.
 */
export function CurrencyField({
  label,
  name,
  required,
  min,
  error,
  defaultValue,
}: CurrencyFieldProps): JSX.Element {
  const [raw, setRaw] = useState<number | "">(defaultValue ?? "");

  const formatted =
    raw === "" || raw === 0
      ? ""
      : new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(raw);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    // Strip everything that isn't a digit
    const digits = e.target.value.replace(/[^\d]/g, "");
    setRaw(digits === "" ? "" : Number(digits));
  }

  const inputClass = `h-11 w-full rounded-lg border pl-8 pr-3.5 text-[15px] outline-none transition focus:border-brand focus:ring-4 focus:ring-indigo-100 ${
    error ? "border-red-400" : "border-gray-200"
  }`;

  return (
    <FieldShell label={label} error={error}>
      <div className="relative">
        {/* ₹ prefix */}
        <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-[15px] text-gray-400">
          ₹
        </span>
        {/* Visible formatted input */}
        <input
          type="text"
          inputMode="numeric"
          autoComplete="off"
          value={formatted}
          onChange={handleChange}
          placeholder="0"
          required={required}
          className={inputClass}
          aria-label={label}
        />
        {/* Hidden input that carries the raw number for FormData */}
        <input
          type="hidden"
          name={name}
          value={raw === "" ? "" : raw}
          readOnly
          data-min={min}
        />
      </div>
    </FieldShell>
  );
}

