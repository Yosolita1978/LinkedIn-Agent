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

  const label = score >= 70 ? "Hot" : score >= 40 ? "Warm" : score >= 10 ? "Cool" : "Cold";

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${bgColor} ${textColor} ${sizeClasses[size]} relative group cursor-default`}
      title={`Warmth: ${score}/100 (${label})`}
    >
      {score}
      <span className="absolute bottom-full right-0 mb-2 px-2 py-1 bg-slate-900 border border-slate-600 rounded text-xs text-slate-300 whitespace-nowrap opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10 shadow-lg">
        Warmth: {score}/100 ({label})
      </span>
    </span>
  );
}
