interface StatusBadgeProps {
  status: string;
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  draft: { bg: "bg-slate-700", text: "text-slate-300" },
  approved: { bg: "bg-blue-500/20", text: "text-blue-400" },
  sent: { bg: "bg-green-500/20", text: "text-green-400" },
  responded: { bg: "bg-emerald-500/20", text: "text-emerald-400" },
};

export default function StatusBadge({ status }: StatusBadgeProps) {
  const style = STATUS_STYLES[status] ?? { bg: "bg-slate-700", text: "text-slate-400" };

  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium capitalize ${style.bg} ${style.text}`}>
      {status}
    </span>
  );
}
