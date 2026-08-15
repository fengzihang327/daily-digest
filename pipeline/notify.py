"""通知推送(可选): Telegram Bot 与 Resend 邮件, 均通过环境变量开关, 未配置时静默跳过。"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger("digest.notify")


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, "").strip() or default


def build_digest_text(payload: dict) -> str:
    """把一期归档渲染成纯文本(Telegram 用)。"""
    lines = [f"📰 每日精读 · {payload['date']}", ""]
    if not payload["items"]:
        lines.append("今日没有通过筛选的高价值文章, 休刊一天。")
        return "\n".join(lines)
    for i, it in enumerate(payload["items"][:3], 1):
        lines.append(f"{i}. [{it['category']}] {it['title']}  (评分 {it['importance_score']})")
        lines.append(f"   {it['tldr']}")
        lines.append(f"   🔗 {it['url']}")
        lines.append("")
    lines.append(f"扫描 {payload['meta']['scanned']} 条, 精选 {len(payload['items'])} 条 — 完整版见 Web 端")
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    token, chat_id = _env("TELEGRAM_BOT_TOKEN"), _env("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Telegram 推送成功")
        return True
    except Exception as e:
        log.warning("Telegram 推送失败: %s", e)
        return False


def _build_html(payload: dict) -> str:
    """把一期归档渲染成极简邮件 HTML。"""
    cards = []
    for it in payload["items"][:5]:
        cards.append(
            f"""
            <div style="margin:18px 0;padding:16px;border:1px solid #e5e7eb;border-radius:10px;">
              <div style="color:#6b7280;font-size:12px;">{it['category']} · 评分 {it['importance_score']}</div>
              <h3 style="margin:6px 0;font-size:16px;"><a href="{it['url']}" style="color:#111827;text-decoration:none;">{it['title']}</a></h3>
              <p style="margin:6px 0;font-size:14px;color:#374151;line-height:1.6;">{it['tldr']}</p>
            </div>"""
        )
    return (
        f"<div style='font-family:-apple-system,sans-serif;max-width:600px;margin:0 auto;'>"
        f"<h2 style='font-size:20px;'>📰 每日精读 · {payload['date']}</h2>"
        + "".join(cards)
        + "</div>"
    )


def send_resend(subject: str, html: str) -> bool:
    api_key = _env("RESEND_API_KEY")
    to = [t.strip() for t in _env("RESEND_TO").split(",") if t.strip()]
    if not (api_key and to):
        return False
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": _env("RESEND_FROM", "Daily Digest <onboarding@resend.dev>"),
                "to": to,
                "subject": subject,
                "html": html,
            },
            timeout=15,
        )
        resp.raise_for_status()
        log.info("Resend 邮件推送成功")
        return True
    except Exception as e:
        log.warning("Resend 邮件推送失败: %s", e)
        return False


def notify_all(payload: dict) -> None:
    """按已配置的通道推送当日 Top 3(全部未配置时静默跳过)。"""
    text = build_digest_text(payload)
    sent_tg = send_telegram(text)
    sent_resend = send_resend(f"📰 每日精读 · {payload['date']}", _build_html(payload))
    if not (sent_tg or sent_resend):
        log.info("未配置任何通知通道(TELEGRAM_* / RESEND_*), 跳过推送")
