/** 与 data/daily_archive/<date>.json 对齐的数据结构 */

export interface DigestItem {
  id: string;
  title: string;
  original_title?: string;
  source: string;
  url: string;
  category: string;
  importance_score: number;
  stage1_score?: number;
  tldr: string;
  first_principles: string;
  counter_intuitive: string;
  published?: string;
}

export interface DigestMeta {
  scanned: number;
  selected: number;
  offline: boolean;
  source_counts: Record<string, number>;
}

export interface Digest {
  date: string;
  generated_at: string;
  meta: DigestMeta;
  items: DigestItem[];
}

/** 与 data/index.json 对齐的数据结构 */
export interface IndexFile {
  latest: {
    date: string;
    updated_at: string;
    item_count: number;
    top: Array<{
      id: string;
      title: string;
      category: string;
      importance_score: number;
      url: string;
    }>;
  } | null;
  days: string[];
}
