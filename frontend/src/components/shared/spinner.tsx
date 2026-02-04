import { cn } from "#/utils/utils";

interface SpinnerProps {
  size?: "sm" | "md" | "lg" | "xl";
  label?: string;
  testId?: string;
  className?: string;
}

const sizeClasses = {
  sm: "w-4 h-4",
  md: "w-6 h-6",
  lg: "w-10 h-10",
  xl: "w-16 h-16",
};

export function Spinner({
  size = "md",
  label,
  testId = "spinner",
  className,
}: SpinnerProps) {
  const spinnerElement = (
    <div
      data-testid={testId}
      className={cn(
        "animate-spin rounded-full border-2 border-current border-t-transparent",
        sizeClasses[size],
        className,
      )}
    />
  );

  if (label) {
    return (
      <div className="flex flex-col items-center gap-2">
        {spinnerElement}
        <span>{label}</span>
      </div>
    );
  }

  return spinnerElement;
}
