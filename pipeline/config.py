"""RSS 数据源与分类常量配置 —— 按需增删数据源, 无需改动主脚本。

个别源的 RSS 地址可能变更, 失效时会在 GitHub Actions 日志中看到对应告警,
替换为新地址即可。
"""
from __future__ import annotations

# name: 媒体名称(会写入 JSON); url: RSS 地址; lang: 语言; max_items: 每源最多抓取条数
RSS_SOURCES = [
    {"name": "Hacker News",          "url": "https://hnrss.org/frontpage",                    "lang": "en", "max_items": 30},
    {"name": "Ars Technica",         "url": "https://feeds.arstechnica.com/arstechnica/index", "lang": "en", "max_items": 20},
    {"name": "The Verge",            "url": "https://www.theverge.com/rss/index.xml",          "lang": "en", "max_items": 20},
    {"name": "MIT Tech Review",      "url": "https://www.technologyreview.com/feed/",          "lang": "en", "max_items": 20},
    {"name": "Nature",               "url": "https://www.nature.com/nature.rss",               "lang": "en", "max_items": 15},
    {"name": "The Economist",        "url": "https://www.economist.com/rss-feeds",             "lang": "en", "max_items": 15},
    {"name": "OpenAI Blog",          "url": "https://openai.com/news/rss.xml",                 "lang": "en", "max_items": 10},
    {"name": "Anthropic",            "url": "https://www.anthropic.com/rss.xml",               "lang": "en", "max_items": 10},
    {"name": "Google AI Blog",       "url": "https://blog.google/technology/ai/rss/",          "lang": "en", "max_items": 10},
    {"name": "36氪",                "url": "https://36kr.com/feed",                           "lang": "zh", "max_items": 20},
    {"name": "少数派",              "url": "https://sspai.com/feed",                          "lang": "zh", "max_items": 20},
    {"name": "爱范儿",              "url": "https://www.ifanr.com/feed",                       "lang": "zh", "max_items": 20},
    {"name": "机器之心",            "url": "https://www.jiqizhixin.com/rss",                   "lang": "zh", "max_items": 20},
]

# 允许的分类(Stage-2 中 Claude 必须从该列表中选择)
CATEGORIES = ["AI前沿", "硬核科技", "全球宏观经济", "前沿思考", "科学探索", "商业财经", "产品设计", "其他"]
