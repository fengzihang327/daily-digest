# Daily Digest · 每日高质量新闻与精读推报

轻量级、自动化、高颜值的个人每日精读系统:
**定时抓取优质 RSS → DeepSeek 两阶段过滤与深度提炼 → Git/JSON 数据沉淀 → PWA 响应式呈现 → 可选推送通知**。

## 架构总览

```
GitHub Actions (每天 09:47 北京时间, Cron)
        │  运行 pipeline/fetch_and_summarize.py
        ▼
┌─────────────────────────────────────────────────────────┐
│ Stage-0  抓取 13 个优质 RSS 源 (feedparser, 去重+新鲜度) │
│ Stage-1  DeepSeek deepseek-chat 批量打分筛选            │  ← 便宜
│          剔除公关稿/水文, score >= 7 入选                │
│ Stage-2  抓正文 (trafilatura/bs4) → DeepSeek 深读        │  ← 精准
│          (deepseek-chat / 可配 deepseek-reasoner)        │
│          输出 tldr / first_principles / counter_intuitive│
└─────────────────────────────────────────────────────────┘
        │
        ▼ 自动 commit 推送
data/daily_archive/2026-08-14.json  ← 每日一期, Git 版本化
data/index.json                     ← 归档索引 + 最新一期 Top3
        │
        ▼ (Git 集成自动触发构建)
Vite + React + Tailwind PWA ──部署──▶ Vercel / Netlify / Cloudflare Pages
        │
        └─▶ 可选推送: Telegram Bot / Resend 邮件(每日 Top 3)
```

## 快速开始(本地)

```bash
# Python 3.10+ (建议 3.12)
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r pipeline/requirements.txt

cp .env.example .env                # 填写 DEEPSEEK_API_KEY 后即可(管线自动读取 .env)
# 或: export DEEPSEEK_API_KEY=sk-...  # 从 https://platform.deepseek.com 获取
python pipeline/fetch_and_summarize.py  # 跑一期今天的, 输出到 data/
```

调试技巧:

```bash
python pipeline/fetch_and_summarize.py --offline          # 不调 API, 只看 RSS 抓取是否正常
python pipeline/fetch_and_summarize.py --date 2026-08-14  # 指定日期补跑
python pipeline/fetch_and_summarize.py --deep-limit 3     # 临时少深读几篇省钱
```

## 环境变量

| 变量 | 必填 | 默认 | 说明 |
|---|---|---|---|
| `DEEPSEEK_API_KEY` | ✅ | — | DeepSeek API Key |
| `DEEPSEEK_BASE_URL` | | `https://api.deepseek.com` | API 地址(OpenAI 兼容格式) |
| `DEEPSEEK_FAST_MODEL` | | `deepseek-chat` | Stage-1 筛选模型 |
| `DEEPSEEK_DEEP_MODEL` | | `deepseek-chat` | Stage-2 深读模型, 可配置为 `deepseek-reasoner` |
| `DEEPSEEK_TEMPERATURE` | | `0.1` | 采样温度(结构化输出建议低温) |
| `MIN_SCORE` | | `7` | Stage-1 筛选阈值 |
| `MAX_ARTICLES` | | `400` | 单日扫描总量上限 |
| `MAX_DEEP_ARTICLES` | | `8` | 单日深读条数上限 |
| `DIGEST_TZ` | | `Asia/Shanghai` | 产出日期时区 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | | — | 配置后启用 Telegram 推送 Top 3 |
| `RESEND_API_KEY` / `RESEND_FROM` / `RESEND_TO` | | — | 配置后启用邮件推送 |

> 结构化输出通过 **JSON Mode**(`response_format: {"type": "json_object"}`)实现;
> 若遇到不支持 JSON Mode 的模型(如部分旧版 `deepseek-reasoner`), 管线会自动降级重试并做防御性解析。

## 数据源定制

编辑 `pipeline/config.py` 中的 `RSS_SOURCES` 即可增删数据源(含英文/中文), 无需改动主脚本。
`CATEGORIES` 为分类枚举, 可随时调整。

## 产出 JSON 结构(每期归档)

`data/daily_archive/YYYY-MM-DD.json`:

```json
{
  "date": "2026-08-14",
  "generated_at": "2026-08-14T09:47:00+08:00",
  "meta": { "scanned": 182, "selected": 8, "source_counts": {...} },
  "items": [
    {
      "id": "2026-08-14-001",
      "title": "中文提炼标题",
      "original_title": "原文标题",
      "source": "来源媒体",
      "url": "原文链接",
      "category": "AI前沿",
      "importance_score": 8.7,
      "stage1_score": 9,
      "tldr": "30秒核心事实总结",
      "first_principles": "第一性原理推导: 为什么重要",
      "counter_intuitive": "反直觉观点或认知增量",
      "published": "2026-08-14T01:00:00+00:00"
    }
  ]
}
```

## 目录结构

```
daily-digest/
├── .github/workflows/daily_digest.yml  # 定时流水线: cron 触发 → 跑管线 → 自动 commit
├── pipeline/                           # 数据管线 (Python 3.10+)
│   ├── fetch_and_summarize.py          # 主脚本: RSS → 两阶段 DeepSeek → JSON
│   ├── config.py                       # RSS 数据源与分类常量
│   ├── notify.py                       # Telegram / Resend 推送
│   └── requirements.txt
├── data/                               # 数据沉淀层 (Git 版本化)
│   ├── index.json                      # 归档索引 + 最新一期 Top3
│   └── daily_archive/                  # 每日一期 JSON
├── frontend/                           # Vite + React + Tailwind PWA
│   ├── src/                            # 看板 / 归档筛选 / 分类标签 / 深读弹窗
│   ├── public/icons/                   # PWA 图标(scripts/gen_icons.py 生成)
│   └── scripts/                        # sync-data.mjs(构建时同步数据) / gen_icons.py
└── README.md
```

## 前端本地开发

```bash
cd frontend
npm install
npm run dev        # 自动把仓库 data/ 同步到 public/data/ 后启动
npm run build      # 类型检查 + 生产构建(含 PWA Service Worker)
```

---

# 阶段五: 部署指南(免费)

## 第 0 步: 推到 GitHub

```bash
cd daily-digest
git init && git add -A && git commit -m "feat: daily digest system"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

## 第 1 步: 配置 GitHub Secrets 与 Variables

仓库 → **Settings → Secrets and variables → Actions**, 分两处配置:

**Secrets(机密, 建议都配):**

| 名称 | 值 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 你的 DeepSeek Key | **必填**, 从 [platform.deepseek.com](https://platform.deepseek.com) → API Keys 创建 |
| `TELEGRAM_BOT_TOKEN` | Bot token | 可选, 用 @BotFather 创建 Bot |
| `TELEGRAM_CHAT_ID` | 你的 chat id | 可选, 给 Bot 发条消息后用 @userinfobot 查询 |
| `RESEND_API_KEY` | Resend Key | 可选, 从 resend.com 获取 |
| `RESEND_FROM` / `RESEND_TO` | 发件人 / 收件人 | 可选 |

**Variables(可调参数, 不配则用默认值):**

| 名称 | 示例值 | 说明 |
|---|---|---|
| `DEEPSEEK_DEEP_MODEL` | `deepseek-reasoner` | 想让深读更"烧脑"就配这个 |
| `MIN_SCORE` | `7` | 筛选阈值 |
| `MAX_ARTICLES` / `MAX_DEEP_ARTICLES` | `400` / `8` | 数量上限 |
| `DIGEST_TZ` | `Asia/Shanghai` | 时区 |

配置完成后, 到仓库 **Actions** 页面点 **Daily Digest Pipeline → Run workflow** 手动跑一次验证(可在输入框指定日期补跑)。日志里应能看到:
`Stage-0 抓取完成 → Stage-1 筛选完成 → Stage-2 深读完成 → 已写入 data/...`

## 第 2 步: 免费部署前端(三选一)

推送 commit 会自动触发部署平台重新构建(包括每晚的数据更新)。

### Vercel(推荐)

1. [vercel.com](https://vercel.com) → **Add New → Project** → Import 你的仓库
2. 配置:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`(自动)
   - **Output Directory**: `dist`(自动)
3. Deploy, 完成。之后的每次 `git push`(含 nightly 数据提交)都会自动重新构建。

### Netlify

1. [netlify.com](https://netlify.com) → **Add new site → Import an existing project** → 选仓库
2. 配置: Base directory `frontend`, Build command `npm run build`, Publish directory `dist`
3. Deploy。

### Cloudflare Pages

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages → Create → Pages → Connect to Git**
2. 配置: Framework preset **Vite**, Root directory `frontend`, Build command `npm run build`, Output `dist`
3. 首次部署后若提示需重新上传产物, 直接部署即可。

## 第 3 步: 安装到手机(PWA)

1. 用手机浏览器打开部署后的网址;
2. iOS Safari: 分享按钮 → **添加到主屏幕**; Android Chrome: 菜单 → **添加到主屏幕** / **安装应用**;
3. 图标为自动生成的琥珀色圆环标记(想换图标: 编辑 `frontend/scripts/gen_icons.py` 后运行 `python3 frontend/scripts/gen_icons.py` 重新生成);
4. Service Worker 已预缓存页面与数据 JSON, **离线也能看最新一期**。

## 常见问题排查

| 现象 | 处理 |
|---|---|
| Actions 报 `缺少环境变量 DEEPSEEK_API_KEY` | Secrets 没配或名字拼错, 检查 Settings → Secrets |
| Actions 日志有 `数据源 [X] 抓取失败` | 该源 RSS 地址失效, 在 `pipeline/config.py` 替换新地址 |
| Actions 日志有 `JSON 解析失败...重试` | DeepSeek 偶发输出不合法, 管线已自动重试; 频繁出现则把 `DEEPSEEK_TEMPERATURE` 调低 |
| 前端没有新一期 | 检查 Actions 是否 commit 成功、部署平台是否收到 push 触发构建 |

## 成本参考

默认配置(深读 8 篇/日)每天约消耗 30-60 万 token, 在 DeepSeek 定价下约为 **每天 ¥0.1-0.5** 量级(以实际用量为准)。
省钱: 调低 `MAX_DEEP_ARTICLES`; 拉满质量: `DEEPSEEK_DEEP_MODEL=deepseek-reasoner`。

## 路线图

- [x] 阶段一: 项目目录架构
- [x] 阶段二: 数据抓取与 AI 处理脚本(DeepSeek, OpenAI 兼容格式)
- [x] 阶段三: GitHub Actions 定时流水线
- [x] 阶段四: Vite + React + Tailwind PWA 前端
- [x] 阶段五: Secrets 配置与免费部署指南
