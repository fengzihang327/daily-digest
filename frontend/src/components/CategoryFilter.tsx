interface CategoryFilterProps {
  categories: string[];
  value: string;
  onChange: (c: string) => void;
}

export function CategoryFilter({ categories, value, onChange }: CategoryFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {categories.map((c) => (
        <button
          key={c}
          onClick={() => onChange(c)}
          className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
            c === value
              ? "border-amber-500 bg-amber-500 text-white"
              : "border-zinc-200 bg-white text-zinc-500 hover:border-amber-400/60 hover:text-amber-600 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-400 dark:hover:text-amber-400"
          }`}
        >
          {c}
        </button>
      ))}
    </div>
  );
}
