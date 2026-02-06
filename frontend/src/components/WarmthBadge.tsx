interface WarmthBadgeProps {
  score: number | null;
  size?: "sm" | "md" | "lg";
}

export default function WarmthBadge({ score, size = "md" }: WarmthBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center rounded-full bg-slate-700 text-slate-400 px-2 py-0.5 text-xs font-medium">
        --
      </span>
    );
  }

  let bgColor: string;
  let textColor: string;

  if (score >= 70) {
    bgColor = "bg-red-500/20";
    textColor = "text-red-400";
  } else if (score >= 40) {
    bgColor = "bg-orange-500/20";
    textColor = "text-orange-400";
  } else if (score >= 10) {
    bgColor = "bg-blue-500/20";
    textColor = "text-blue-400";
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
