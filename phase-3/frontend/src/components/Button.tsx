import type { ButtonHTMLAttributes, PropsWithChildren } from "react";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "destructive";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  loading?: boolean;
}

const variants: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-hover border-transparent",
  secondary: "bg-white text-gray-700 border-gray-200 hover:bg-gray-50",
  ghost: "bg-transparent text-brand border-transparent hover:bg-indigo-50",
  destructive: "bg-white text-risk-highText border-risk-highBorder hover:bg-risk-highBg",
};

export function Button({
  children,
  className = "",
  variant = "primary",
  loading = false,
  disabled,
  ...props
}: PropsWithChildren<ButtonProps>): JSX.Element {
  return (
    <button
      className={`inline-flex h-11 items-center justify-center gap-2 rounded-lg border px-5 text-[15px] font-medium transition active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 ${variants[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
