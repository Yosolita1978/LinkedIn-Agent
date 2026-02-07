interface PriorityBadgeProps {
  score: number;
  size?: "sm" | "md" | "lg";
}

export default function PriorityBadge({ score, size = "md" }: PriorityBadgeProps) {
  let bgColor: string;
  let textColor: string;

  if (score >= 70) {
    bgColor = "bg-emerald-500/20";
    textColor = "text-emerald-400";
  } else if (score >= 40) {
    bgColor = "bg-green-500/20";
    textColor = "text-green-400";
  } else if (score >= 20) {
    bgColor = "bg-teal-500/20";
    textColor = "text-teal-400";
  } else {
    bgColor = "bg-slate-700";
    textColor = "text-slate-400";
  }

  const sizeClasses = {
    sm: "px-1.5 py-0.5 text-xs",
    md: "px-2 py-0.5 text-sm",
    lg: "px-3 py-1 text-base font-semibold",
  };

  return (
    <span className={`inline-flex items-center rounded-full font-medium ${bgColor} ${textColor} ${sizeClasses[size]}`}>
      {score}
    </span>
  );
}
