interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorMessage({ message, onRetry }: ErrorMessageProps) {
  return (
    <div className="rounded-lg bg-red-500/10 border border-red-500/30 p-4">
      <p className="text-sm text-red-400">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-sm font-medium text-red-400 hover:text-red-300"
        >
          Try again
        </button>
      )}
    </div>
  );
}
