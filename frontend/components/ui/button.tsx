import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/ui/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "md" | "lg";

export type ButtonProps = {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  /** Shows a busy state and blocks activation. */
  loading?: boolean;
  children: ReactNode;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className">;

const VARIANT: Record<ButtonVariant, string> = {
  // White on --accent is 5.87:1.
  primary: "bg-accent text-surface hover:opacity-90 disabled:hover:opacity-100",
  secondary: "bg-surface text-primary border border-control-border hover:bg-bg",
  ghost: "bg-transparent text-accent hover:bg-accent-soft",
};

const SIZE: Record<ButtonSize, string> = {
  // Both sizes clear the ~44px minimum touch target from section 15.
  md: "min-h-touch px-4 text-support",
  lg: "min-h-[52px] px-6 text-body",
};

export function Button({
  variant = "primary",
  size = "md",
  fullWidth = false,
  loading = false,
  disabled = false,
  type = "button",
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;

  return (
    <button
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-control font-medium",
        "transition-[background-color,opacity,border-color] duration-fast ease-standard",
        "disabled:cursor-not-allowed disabled:opacity-50",
        VARIANT[variant],
        SIZE[size],
        fullWidth && "w-full",
      )}
      {...props}
    >
      {loading ? (
        <>
          <span
            aria-hidden="true"
            className="size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
          />
          {/* Announced instead of relying on the spinner alone. */}
          <span className="sr-only">Loading</span>
        </>
      ) : null}
      {children}
    </button>
  );
}
