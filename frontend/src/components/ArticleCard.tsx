import type { DigestItem } from "../lib/types";

export function ArticleCard({ item, onClick }: { item: DigestItem; onClick: () => void }) {
  return (
    <article
      onClick={onClick}
      className="group cursor-pointer rounded-xl border border-zinc-200 bg-white p-5 transition-all hover:-translate-y-0.5 hover:border-amber-400/60 hover:shadow-lg hover:shadow-amber-500/5 dark:border-zinc-800 dark:bg-zinc-900"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
          {item.category}
        </span>
        <span className="font-mono text-xs text-zinc-400">
          {typeof item.importance_score === "number" ? item.importance_score.toFixed(1) : item.importance_score}
        </span>
      </div>

      <h2 className="mt-3 text-lg font-semibold leading-snug tracking-tight transition-colors group-hover:text-amber-600 dark:group-hover:text-amber-400">
        {item.title}
      </h2>

      <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-zinc-500 dark:text-zinc-400">
        {item.tldr}
      </p>

      <div className="mt-3 flex items-center gap-2 text-xs text-zinc-400">
        <span>{item.source}</span>
        {item.published && (
          <>
            <span>·</span>
            <span>{new Date(item.published).toLocaleDateString("zh-CN")}</span>
          </>
        )}
        <span className="ml-auto opacity-0 transition-opacity group-hover:opacity-100">
          阅读精读 ↗
        </span>
      </div>
    </article>
  );
}
