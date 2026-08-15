export function EmptyState({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex flex-col items-center gap-2 py-20 text-center">
      <p className="text-lg font-medium">{title}</p>
      <p className="max-w-md text-sm leading-relaxed text-zinc-400">{message}</p>
    </div>
  );
}
