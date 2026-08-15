#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日高质量新闻与精读推报 —— 数据管线主脚本
================================================
流程:
  1) 抓取所有配置的 RSS 数据源, 汇总(标题 + 摘要), 跨源去重 + 新鲜度过滤
  2) Stage-1: DeepSeek 快速模型批量打分筛选, 剔除公关稿/水文/情绪输出, 保留 >= MIN_SCORE 的文章
  3) 对入选文章抓取正文 (trafilatura, 失败回退 BeautifulSoup / RSS 摘要)
  4) Stage-2: DeepSeek 深度模型按结构化 JSON 提炼: tldr / first_principles / counter_intuitive ...
  5) 写入 data/daily_archive/<date>.json 并更新 data/index.json
  6) 可选: Telegram / Resend 推送当日 Top 3

LLM 调用: DeepSeek API (OpenAI 兼容格式, base_url=https://api.deepseek.com),
使用 JSON Mode (response_format={"type": "json_object"}) 保证结构化输出。

用法:
  python pipeline/fetch_and_summarize.py                    # 按今天(DIGEST_TZ 时区)运行
  python pipeline/fetch_and_summarize.py --date 2026-08-14  # 指定日期补跑
  python pipeline/fetch_and_summarize.py --limit 150 --deep-limit 8 --skip-notify
  python pipeline/fetch_and_summarize.py --offline          # 只抓 RSS, 不调用 API(调试用)

环境变量:
  DEEPSEEK_API_KEY        必需
  DEEPSEEK_BASE_URL       API 地址, 默认 https://api.deepseek.com
  DEEPSEEK_FAST_MODEL     Stage-1 筛选模型, 默认 deepseek-chat
  DEEPSEEK_DEEP_MODEL     Stage-2 深读模型, 默认 deepseek-chat(可配置为 deepseek-reasoner)
  DEEPSEEK_TEMPERATURE    采样温度, 默认 0.1(结构化输出场景建议低温)
  MIN_SCORE               筛选阈值, 默认 7
  MAX_ARTICLES            扫描总量上限, 默认 400
  MAX_DEEP_ARTICLES       Stage-2 深读数量上限, 默认 8
  DIGEST_TZ               产出日期时区, 默认 Asia/Shanghai
  TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID    可选, Telegram 推送
  RESEND_API_KEY / RESEND_FROM / RESEND_TO 可选, 邮件推送
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from zoneinfo import ZoneInfo

import feedparser
import requests
from openai import APIConnectionError, APITimeoutError, APIStatusError, BadRequestError, OpenAI
from bs4 import BeautifulSoup
import trafilatura

# 保证无论从哪个目录执行都能 import 到同目录的 config / notify
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config
import notify

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
ARCHIVE_DIR = DATA_DIR / "daily_archive"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("digest")

USER_AGENT = "DailyDigestBot/1.0 (personal daily digest)"
REQUEST_HEADERS = {"User-Agent": USER_AGENT}

MAX_TEXT_CHARS = 12_000   # 单篇正文送入 Stage-2 的最大字符数
MAX_AGE_HOURS = 72        # 超过该时长的旧闻直接丢弃(设为 0 关闭)
STAGE1_CHUNK = 30         # Stage-1 每批打分条数
API_ATTEMPTS = 4          # 单次 API 调用最大尝试次数


# ── .env 加载 ────────────────────────────────────────────────────────

def _load_env_file(path: Path) -> None:
    """极简 .env 加载: 只设置未定义的环境变量, 不覆盖已有值, 无需第三方依赖。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


# ── 配置 ────────────────────────────────────────────────────────────

def env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, "").strip() or default


def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, "").strip() or default)
    except ValueError:
        return default


def env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, "").strip() or default)
    except ValueError:
        return default


@dataclass
class Settings:
    api_key: str
    base_url: str
    fast_model: str
    deep_model: str
    temperature: float
    min_score: int
    max_articles: int
    deep_limit: int
    max_text_chars: int
    tz: Any


CFG: Settings = None  # type: ignore[assignment]


def load_settings(offline: bool) -> Settings:
    api_key = env_str("DEEPSEEK_API_KEY")
    if not api_key and not offline:
        log.error("缺少环境变量 DEEPSEEK_API_KEY(本地调试可加 --offline 跳过 API)")
        raise SystemExit(1)
    tz_name = env_str("DIGEST_TZ", "Asia/Shanghai")
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        log.warning("无法解析时区 %s, 回退 UTC", tz_name)
        tz = timezone.utc
    return Settings(
        api_key=api_key,
        base_url=env_str("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        fast_model=env_str("DEEPSEEK_FAST_MODEL", "deepseek-chat"),
        deep_model=env_str("DEEPSEEK_DEEP_MODEL", "deepseek-chat"),  # 可配置为 deepseek-reasoner
        temperature=env_float("DEEPSEEK_TEMPERATURE", 0.1),
        min_score=env_int("MIN_SCORE", 7),
        max_articles=env_int("MAX_ARTICLES", 400),
        deep_limit=env_int("MAX_DEEP_ARTICLES", 8),
        max_text_chars=MAX_TEXT_CHARS,
        tz=tz,
    )


# ── 数据模型与工具函数 ───────────────────────────────────────────────

@dataclass
class Item:
    source: str
    title: str
    summary: str
    url: str
    published: str = ""
    text: str = ""
    score: int = 0
    score_reason: str = ""
    analysis: dict = field(default_factory=dict)


HTML_TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def _strip_html(s: str) -> str:
    return WS_RE.sub(" ", HTML_TAG_RE.sub(" ", s or "")).strip()


def _dedup_key(title: str, url: str) -> str:
    base = re.sub(r"[^\w一-鿿]", "", title.lower())[:60]
    if url:
        base += url.split("?")[0][-40:]
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def _parse_pub(entry: Any):
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            return datetime(*st[:6], tzinfo=timezone.utc)
    return None


def fetch_all(sources: list[dict], max_articles: int) -> list[Item]:
    """抓取全部 RSS 源: 单源失败不影响整体, 输出跨源去重后的条目列表。"""
    items: list[Item] = []
    seen: set[str] = set()
    now = datetime.now(timezone.utc)

    for src in sources:
        try:
            resp = requests.get(src["url"], headers=REQUEST_HEADERS, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:
            log.warning("数据源 [%s] 抓取失败: %s", src.get("name"), e)
            continue

        count = 0
        for entry in feed.entries:
            if count >= src.get("max_items", 20):
                break
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue
            summary = _strip_html(entry.get("summary") or entry.get("description") or "")[:500]

            key = _dedup_key(title, link)
            if key in seen:
                continue
            seen.add(key)

            published = _parse_pub(entry)
            if MAX_AGE_HOURS and published and (now - published).total_seconds() > MAX_AGE_HOURS * 3600:
                continue

            items.append(Item(
                source=src["name"],
                title=title,
                summary=summary,
                url=link,
                published=published.isoformat() if published else "",
            ))
            count += 1
            if len(items) >= max_articles:
                return items

    return items


# ── Stage-1: 快速筛选 ────────────────────────────────────────────────

SYSTEM_STAGE1 = """你是一位为高端读者服务的主编, 负责从海量资讯中筛选出真正值得精读的新闻。

评分标准(0-10 整数):
- 10 分: 具有全球/行业级长期影响力、可能改变认知或格局的大事
- 8-9 分: 重要实质进展, 值得读者花 5 分钟精读
- 7 分 : 有价值的新资讯, 值得收录
- 4-6 分: 普通行业动态、常规资讯
- 0-3 分: 公关稿、软文、重复报道、纯情绪/观点输出、八卦猎奇

规则:
- 只依据提供的标题与摘要判断, 不要臆测正文内容
- 每条都必须打分, 分数必须为 0-10 的整数, 理由不超过一句话
- 请以 json 对象格式返回打分结果, 结构必须为:
  {"scores": [{"index": 0, "score": 8, "reason": "一句话理由"}]}
- scores 数组必须覆盖用户消息中的每一条新闻
- 不要输出 json 以外的任何文字"""


def stage1_filter(client: OpenAI, settings: Settings, items: list[Item]) -> list[Item]:
    """Stage-1: 分批打分筛选, 返回 score >= min_score 的条目(按分数降序)。"""
    kept: list[Item] = []
    for start in range(0, len(items), STAGE1_CHUNK):
        chunk = items[start:start + STAGE1_CHUNK]
        numbered = [
            {"index": i, "title": it.title, "summary": it.summary, "source": it.source}
            for i, it in enumerate(chunk)
        ]
        user = f"请为以下 {len(chunk)} 条新闻逐条打分并给出理由:\n" + json.dumps(numbered, ensure_ascii=False)
        try:
            result = call_with_retry(
                lambda: _chat_json(client, settings.fast_model, SYSTEM_STAGE1, user, 4096)
            )
        except Exception as e:
            log.error("Stage-1 第 %d 批打分失败, 跳过该批: %s", start // STAGE1_CHUNK + 1, e)
            continue

        scores = {s.get("index"): s for s in result.get("scores", []) if isinstance(s, dict)}
        for i, it in enumerate(chunk):
            s = scores.get(i)
            if not s:
                continue
            try:
                it.score = int(s.get("score", 0))
            except (TypeError, ValueError):
                it.score = 0
            it.score_reason = str(s.get("reason", ""))
            if it.score >= settings.min_score:
                kept.append(it)

    kept.sort(key=lambda it: it.score, reverse=True)
    return kept


# ── Stage-2: 深度认知提炼 ────────────────────────────────────────────

SYSTEM_STAGE2 = """你是「每日精读」栏目的资深主笔, 服务一群聪明、忙碌、追求认知增量的读者。请基于提供的原文进行深度提炼。

输出要求(字段含义):
- title: 中文提炼标题, 10-24 字, 点出核心增量, 避免标题党
- source: 来源媒体名称(取自输入, 一般照抄)
- category: 从以下分类中选择最贴切的一个: {categories}
- importance_score: 0-10 的数字, 保留一位小数
- tldr: 30 秒核心事实总结, 用 1-2 句话讲清楚「发生了什么」
- first_principles: 从第一性原理推导「为什么重要」——事件背后的底层驱动力(物理规律、算力/成本曲线、商业模式本质、宏观传导机制等), 2-4 句话, 拒绝空话套话
- counter_intuitive: 反直觉的观点、大多数人容易误读的地方, 或本文提供的关键认知增量, 1-2 句话

规则:
- 只依据提供的正文提炼; 正文明显不完整时(如登录墙)以标题与摘要为准
- 表述精炼有力, 全部用中文输出
- 请以 json 对象格式返回, 必须包含且仅包含以上 7 个字段, 例如:
  {{"title": "...", "source": "...", "category": "AI前沿", "importance_score": 8.5,
    "tldr": "...", "first_principles": "...", "counter_intuitive": "..."}}
- 不要输出 json 以外的任何文字"""


def extract_text(settings: Settings, item: Item) -> str:
    """抓取正文: trafilatura 优先, 失败回退 BeautifulSoup, 再回退 RSS 摘要。"""
    if item.text:
        return item.text
    text = ""
    if item.url:
        try:
            html = trafilatura.fetch_url(item.url)
            if html:
                extracted = trafilatura.extract(
                    html, include_comments=False, include_tables=False, include_links=False
                )
                if extracted and len(extracted) >= 150:
                    text = extracted
        except Exception as e:
            log.debug("trafilatura 提取失败 %s: %s", item.url, e)

        if len(text) < 150:
            try:
                resp = requests.get(item.url, headers=REQUEST_HEADERS, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
                    tag.decompose()
                text = soup.get_text(" ", strip=True)
            except Exception as e:
                log.debug("BeautifulSoup 回退失败 %s: %s", item.url, e)

    if len(text) < 150:
        text = item.summary
    item.text = text[: settings.max_text_chars]
    return item.text


def normalize_analysis(raw: dict) -> dict:
    """把模型返回的 JSON 规整为统一结构: 类型纠正 + 分类枚举兜底。"""
    category = str(raw.get("category") or "其他")
    if category not in config.CATEGORIES:
        category = "其他"
    try:
        score = float(raw.get("importance_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    return {
        "title": str(raw.get("title") or "").strip(),
        "source": str(raw.get("source") or "").strip(),
        "category": category,
        "importance_score": round(score, 1),
        "tldr": str(raw.get("tldr") or "").strip(),
        "first_principles": str(raw.get("first_principles") or "").strip(),
        "counter_intuitive": str(raw.get("counter_intuitive") or "").strip(),
    }


def stage2_deep(client: OpenAI, settings: Settings, item: Item) -> dict:
    """Stage-2: 对单篇文章做深度认知提炼, 返回规整后的结构化分析 dict。"""
    text = extract_text(settings, item)
    system = SYSTEM_STAGE2.format(categories=", ".join(config.CATEGORIES))
    user = (
        f"来源媒体: {item.source}\n"
        f"原文标题: {item.title}\n"
        f"原文链接: {item.url}\n"
        f"发布时间: {item.published or '未知'}\n\n"
        f"【正文】\n{text}"
    )
    raw = call_with_retry(lambda: _chat_json(client, settings.deep_model, system, user, 2048))
    return normalize_analysis(raw)


# ── DeepSeek (OpenAI 兼容) API 调用基础设施 ─────────────────────────

def _parse_json(content: str) -> Any:
    """防御性 JSON 解析: 容忍 markdown 代码围栏与前后杂音。"""
    if not content:
        raise ValueError("返回内容为空")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.MULTILINE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError("无法解析模型返回的 JSON")


def _chat_json(client: OpenAI, model: str, system: str, user: str, max_tokens: int) -> dict:
    """调用 DeepSeek (OpenAI 兼容) 并以 JSON Mode 返回结构化结果。

    deepseek-reasoner 对 JSON Mode / temperature 的兼容性历史上存在差异,
    遇到 400 时自动降级: 去掉 response_format 与 temperature 重试一次, 再做防御性解析。
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    kwargs: dict[str, Any] = dict(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=CFG.temperature,
        response_format={"type": "json_object"},
    )
    try:
        resp = client.chat.completions.create(**kwargs)
    except BadRequestError:
        # 部分模型(如旧版 deepseek-reasoner)不支持 response_format / temperature
        log.warning("JSON Mode 请求被拒(模型 %s), 降级为普通模式重试", model)
        kwargs.pop("response_format", None)
        kwargs.pop("temperature", None)
        resp = client.chat.completions.create(**kwargs)

    content = resp.choices[0].message.content or ""
    data = _parse_json(content)
    if not isinstance(data, dict):
        raise ValueError("模型未返回合法的 json 对象")
    return data


def call_with_retry(fn: Callable[[], dict]) -> dict:
    """带指数退避的重试: 网络错误/限流(429)/5xx/JSON 解析失败时重试; 其余 4xx 立即抛出。"""
    last: Exception | None = None
    for attempt in range(1, API_ATTEMPTS + 1):
        try:
            return fn()
        except ValueError as e:
            last = e
            log.warning("JSON 解析失败/返回不合法(第 %d 次), 重试中...", attempt)
        except (APIConnectionError, APITimeoutError) as e:
            last = e
            log.warning("网络错误(第 %d 次): %s", attempt, e)
        except APIStatusError as e:
            last = e
            if e.status_code not in (429, 500, 502, 503, 529):
                raise  # 其余 4xx 不重试
            log.warning("API %s 错误(第 %d 次): %s", e.status_code, attempt, e)
        time.sleep(min(2 ** attempt + random.uniform(0, 1), 30))
    raise RuntimeError(f"API 调用重试 {API_ATTEMPTS} 次仍失败: {last}") from last


# ── 落盘 ─────────────────────────────────────────────────────────────

def build_payload(date_str: str, scanned: list[Item], deep: list[Item],
                  offline: bool, started_at: datetime) -> dict:
    items_out: list[dict] = []
    for it in deep:
        a = it.analysis or {}
        if offline:
            items_out.append({
                "title": it.title,
                "source": it.source,
                "url": it.url,
                "category": "其他",
                "importance_score": 0,
                "tldr": it.summary[:200],
                "first_principles": "",
                "counter_intuitive": "",
                "published": it.published,
            })
        else:
            items_out.append({
                "title": a.get("title") or it.title,
                "original_title": it.title,
                "source": a.get("source") or it.source,
                "url": it.url,
                "category": a.get("category", "其他"),
                "importance_score": a.get("importance_score", it.score),
                "stage1_score": it.score,
                "stage1_reason": it.score_reason,
                "tldr": a.get("tldr", ""),
                "first_principles": a.get("first_principles", ""),
                "counter_intuitive": a.get("counter_intuitive", ""),
                "published": it.published,
            })

    # 按重要性降序后统一编号, 保证 id 稳定且 Top 3 语义清晰
    items_out.sort(key=lambda x: float(x.get("importance_score") or 0), reverse=True)
    for i, it in enumerate(items_out, 1):
        it["id"] = f"{date_str}-{i:03d}"

    source_counts: dict[str, int] = {}
    for it in scanned:
        source_counts[it.source] = source_counts.get(it.source, 0) + 1

    return {
        "date": date_str,
        "generated_at": started_at.isoformat(timespec="seconds"),
        "meta": {
            "scanned": len(scanned),
            "selected": len(deep),
            "offline": offline,
            "source_counts": source_counts,
        },
        "items": items_out,
    }


def write_files(payload: dict) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    date_str = payload["date"]

    archive_path = ARCHIVE_DIR / f"{date_str}.json"
    archive_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("已写入 %s (%d 条)", archive_path, len(payload["items"]))

    index_path = DATA_DIR / "index.json"
    index: dict = {}
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            index = {}
    days = list(dict.fromkeys([date_str] + index.get("days", [])))
    index.update({
        "latest": {
            "date": date_str,
            "updated_at": datetime.now(CFG.tz).isoformat(timespec="seconds"),
            "item_count": len(payload["items"]),
            "top": [
                {"id": it["id"], "title": it["title"], "category": it["category"],
                 "importance_score": it["importance_score"], "url": it["url"]}
                for it in payload["items"][:3]
            ],
        },
        "days": days,
    })
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("已更新 %s (共 %d 个归档日)", index_path, len(days))
    return archive_path


# ── 主流程 ───────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    global CFG
    _load_env_file(ROOT / ".env")   # 本地开发: 支持 .env 文件(已 gitignore)
    ap = argparse.ArgumentParser(description="每日新闻精读推报 · 数据管线")
    ap.add_argument("--date", default="", help="目标日期 YYYY-MM-DD, 默认按 DIGEST_TZ 时区的今天")
    ap.add_argument("--limit", type=int, default=0, help="扫描总量上限(覆盖 MAX_ARTICLES)")
    ap.add_argument("--deep-limit", type=int, default=0, help="Stage-2 深读数量上限(覆盖 MAX_DEEP_ARTICLES)")
    ap.add_argument("--skip-notify", action="store_true", help="跳过 Telegram/邮件推送")
    ap.add_argument("--offline", action="store_true", help="只抓取 RSS, 不调用 API(调试用)")
    args = ap.parse_args(argv)

    CFG = load_settings(offline=args.offline)
    if args.limit:
        CFG.max_articles = args.limit
    if args.deep_limit:
        CFG.deep_limit = args.deep_limit

    started_at = datetime.now(CFG.tz)
    date_str = args.date or started_at.strftime("%Y-%m-%d")
    log.info("== 每日精读流水线启动  date=%s  tz=%s  fast=%s  deep=%s ==",
             date_str, CFG.tz, CFG.fast_model, CFG.deep_model)

    items = fetch_all(config.RSS_SOURCES, CFG.max_articles)
    log.info("Stage-0 抓取完成: 共 %d 条(跨源去重后)", len(items))
    if not items:
        log.warning("没有抓到任何条目, 仍会生成空归档文件便于排查")
        payload = build_payload(date_str, items, [], args.offline, started_at)
        write_files(payload)
        return 0

    deep: list[Item] = []
    if not args.offline:
        client = OpenAI(api_key=CFG.api_key, base_url=CFG.base_url, timeout=120)
        kept = stage1_filter(client, CFG, items)
        log.info("Stage-1 筛选完成: %d -> 保留 %d 条(阈值 >= %d)", len(items), len(kept), CFG.min_score)

        candidates = kept[: CFG.deep_limit]
        for n, it in enumerate(candidates, 1):
            try:
                it.analysis = stage2_deep(client, CFG, it)
                a = it.analysis
                log.info("  [%d/%d] %s | %s (%.1f)", n, len(candidates),
                         a.get("category", "?"), a.get("title", it.title),
                         float(a.get("importance_score") or 0))
                deep.append(it)
            except Exception as e:
                log.error("  [%d/%d] 深读失败 %s: %s", n, len(candidates), it.title, e)
        log.info("Stage-2 深读完成: %d 条", len(deep))
    else:
        deep = items
        log.info("离线模式: 跳过 API, 输出原始条目 %d 条", len(items))

    payload = build_payload(date_str, items, deep, args.offline, started_at)
    write_files(payload)

    log.info("== 流水线完成  date=%s 扫描=%d 精选=%d ==", date_str, len(items), len(payload["items"]))

    if not args.skip_notify and not args.offline and payload["items"]:
        notify.notify_all(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
