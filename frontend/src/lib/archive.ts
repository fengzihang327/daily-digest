import type { Digest, IndexFile } from "./types";

/**
 * 数据读取层: 构建时由 scripts/sync-data.mjs 把仓库 data/ 复制进 public/data/,
 * 运行时直接 fetch 静态 JSON(可被 Service Worker 离线缓存)。
 */

function dataUrl(path: string): string {
  return `${import.meta.env.BASE_URL}data/${path}`;
}

export async function fetchIndex(): Promise<IndexFile> {
  const res = await fetch(dataUrl("index.json"));
  if (!res.ok) throw new Error(`index.json HTTP ${res.status}`);
  return res.json();
}

export async function fetchDigest(date: string): Promise<Digest> {
  const res = await fetch(dataUrl(`daily_archive/${date}.json`));
  if (!res.ok) throw new Error(`${date}.json HTTP ${res.status}`);
  return res.json();
}
