import { ThemeToggle } from "./ThemeToggle";

interface HeaderProps {
  days: string[];
  date: string;
  onDateChange: (d: string) => void;
}

export function Header({ days, date, onDateChange }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 border-b border-zinc-200/70 bg-zinc-50/80 backdrop-blur dark:border-zinc-800/70 dark:bg-zinc-950/80">
      <div className="mx-auto flex w-full max-w-3xl items-center justify-between px-4 py-4 sm:px-6">
        <div className="flex items-baseline gap-3">
          <h1 className="text-lg font-bold tracking-tight">每日精读</h1>
          <span className="hidden text-xs text-zinc-400 sm:inline">高质量新闻与深度认知</span>
        </div>

        <div className="flex items-center gap-2">
          <select
            value={date}
            onChange={(e) => onDateChange(e.target.value)}
            aria-label="选择日期"
            className="rounded-lg border border-zinc-200 bg-white px-2.5 py-1.5 text-xs text-zinc-600 outline-none transition-colors focus:ring-2 focus:ring-amber-500/40 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-300"
          >
            {days.length === 0 && <option value="">暂无归档</option>}
            {days.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
