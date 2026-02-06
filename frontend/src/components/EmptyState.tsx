interface EmptyStateProps {
  title: string;
  description?: string;
}

export default function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <p className="text-slate-400 text-lg">{title}</p>
      {description && <p className="text-slate-500 text-sm mt-1">{description}</p>}
    </div>
  );
}
