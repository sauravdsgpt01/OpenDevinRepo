import { cn } from "@heroui/react";
import { Typography } from "#/ui/typography";

interface StepOptionProps {
  id: string;
  label: string;
  selected: boolean;
  onClick: () => void;
}

export function StepOption({ id, label, selected, onClick }: StepOptionProps) {
  return (
    <button
      data-testid={`step-option-${id}`}
      type="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick();
        }
      }}
      className={cn(
        "h-10 w-full rounded-md border text-left px-4 transition-colors text-white cursor-pointer",
        selected
          ? "border-white bg-[#3a3a3a]"
          : "border-[#3a3a3a] hover:bg-[#3a3a3a]",
      )}
    >
      <Typography.Text className="text-sm font-medium text-content">
        {label}
      </Typography.Text>
    </button>
  );
}
