import { useCallback, useEffect, useMemo, useState } from "react";
import type { Digest, DigestItem, IndexFile } from "./lib/types";
import { fetchDigest, fetchIndex } from "./lib/archive";
import { ArticleCard } from "./components/ArticleCard";
import { ArticleModal } from "./components/ArticleModal";
import { CategoryFilter } from "./components/CategoryFilter";
import { EmptyState } from "./components/EmptyState";
import { Header } from "./components/Header";

export default function App() {
  const [index, setIndex] = useState<IndexFile | null>(null);
  const [date, setDate] = useState("");
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState("全部");
  const [selected, setSelected] = useState<DigestItem | null>(null);

  // 1. 加载归档索引(日期列表 + 最新一期), 默认展示最新
  useEffect(() => {
    fetchIndex()
      .then((idx) => {
        setIndex(idx);
        setDate(idx.latest?.date ?? idx.days[0] ?? "");
      })
      .catch((e) => setError(`加载索引失败: ${e instanceof Error ? e.message : String(e)}`))
      .finally(() => setLoading(false));
  }, []);

  // 2. 切换日期时加载对应归档
  useEffect(() => {
    if (!date) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchDigest(date)
      .then((d) => {
        if (!cancelled) setDigest(d);
      })
      .catch((e) => {
        if (!cancelled) setError(`加载 ${date} 归档失败: ${e instanceof Error ? e.message : String(e)}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  const categories = useMemo(() => {
    const set = new Set((digest?.items ?? []).map((it) => it.category));
    return ["全部", ...Array.from(set).sort()];
  }, [digest]);

  const items = useMemo(
    () => (digest?.items ?? []).filter((it) => category === "全部" || it.category === category),
    [digest, category]
  );

  const handleDateChange = useCallback((d: string) => {
    setDate(d);
    setCategory("全部");
    setSelected(null);
  }, []);

  const hasData = index !== null && date !== "";

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-900 antialiased transition-colors dark:bg-zinc-950 dark:text-zinc-100">
      <Header days={index?.days ?? []} date={date} onDateChange={handleDateChange} />

      <main className="mx-auto w-full max-w-3xl px-4 pb-24 pt-8 sm:px-6">
        {loading && <p className="py-16 text-center text-sm text-zinc-400">加载中…</p>}

        {!loading && error && <EmptyState title="出错了" message={error} />}

        {!loading && !error && hasData && digest && digest.items.length === 0 && (
          <EmptyState title="今日休刊" message="没有通过筛选的高价值文章。明天见。" />
        )}

        {!loading && !error && !hasData && (
          <EmptyState title="暂无归档" message="数据由 GitHub Actions 每日自动生成, 首期发布后这里会显示内容。" />
        )}

        {!loading && !error && digest && digest.items.length > 0 && (
          <>
            <div className="mb-6 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-zinc-400">
              <span>扫描 {digest.meta.scanned} 条</span>
              <span>·</span>
              <span>精选 {digest.items.length} 条</span>
              <span>·</span>
              <span>
                生成于 {new Date(digest.generated_at).toLocaleString("zh-CN", { hour12: false })}
              </span>
            </div>

            <CategoryFilter categories={categories} value={category} onChange={setCategory} />

            <div className="mt-6 space-y-4">
              {items.map((it) => (
                <ArticleCard key={it.id} item={it} onClick={() => setSelected(it)} />
              ))}
              {items.length === 0 && (
                <p className="py-8 text-center text-sm text-zinc-400">该分类下暂无文章。</p>
              )}
            </div>
          </>
        )}
      </main>

      <footer className="pb-10 text-center text-xs text-zinc-400">
        GitHub Actions + DeepSeek 每日自动生成 · 数据沉淀于 Git 仓库
      </footer>

      {selected && <ArticleModal item={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
