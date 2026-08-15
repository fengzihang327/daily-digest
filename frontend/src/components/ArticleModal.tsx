import { useEffect } from "react";
import type { ReactNode } from "react";
import type { DigestItem } from "../lib/types";

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <section className="mt-6">
      <h3 className="text-xs font-semibold uppercase tracking-widest text-zinc-400">{label}</h3>
      <p className="mt-2 text-sm leading-relaxed text-zinc-700 dark:text-zinc-300">{children}</p>
    </section>
  );
}

export function ArticleModal({ item, onClose }: { item: DigestItem; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-4 backdrop-blur-sm sm:p-8"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="relative w-full max-w-2xl rounded-2xl border border-zinc-200 bg-white p-6 shadow-2xl dark:border-zinc-700 dark:bg-zinc-900 sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          aria-label="关闭"
          className="absolute right-4 top-4 rounded-lg p-1.5 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 3l10 10M13 3L3 13" strokeLinecap="round" />
          </svg>
        </button>

        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 font-medium text-amber-600 dark:text-amber-400">
            {item.category}
          </span>
          <span className="text-zinc-400">{item.source}</span>
          <span className="ml-auto font-mono text-zinc-400">
            {typeof item.importance_score === "number" ? item.importance_score.toFixed(1) : item.importance_score} / 10
          </span>
        </div>

        <h2 className="mt-4 text-2xl font-semibold leading-snug tracking-tight">{item.title}</h2>
        {item.original_title && item.original_title !== item.title && (
          <p className="mt-1 text-sm text-zinc-400">原文: {item.original_title}</p>
        )}

        <Section label="TLDR · 30 秒核心事实">{item.tldr}</Section>
        <Section label="第一性原理 · 为什么重要">{item.first_principles}</Section>
        <Section label="反直觉 · 认知增量">{item.counter_intuitive}</Section>

        <div className="mt-8 flex items-center gap-3">
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer noopener"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-amber-500 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-amber-400"
          >
            阅读原文 ↗
          </a>
          <button
            onClick={onClose}
            className="rounded-lg border border-zinc-200 px-4 py-2 text-sm font-medium text-zinc-600 transition-colors hover:bg-zinc-100 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
