interface SegmentBadgeProps {
  segment: string;
}

const SEGMENT_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  mujertech: { bg: "bg-purple-500/20", text: "text-purple-400", label: "MujerTech" },
  cascadia: { bg: "bg-teal-500/20", text: "text-teal-400", label: "Cascadia AI" },
  job_target: { bg: "bg-amber-500/20", text: "text-amber-400", label: "Job Target" },
};

export default function SegmentBadge({ segment }: SegmentBadgeProps) {
  const style = SEGMENT_STYLES[segment] ?? { bg: "bg-slate-700", text: "text-slate-400", label: segment };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}
