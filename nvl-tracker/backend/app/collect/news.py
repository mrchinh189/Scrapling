"""Collector tin tức thị trường (Google News RSS) — chỉ tiêu đề + tóm tắt + link.

Miễn phí, không cần key. ⚖️ KHÔNG lưu full-text / nội dung trả phí.
Tách `parse_google_news_rss` (thuần) khỏi phần tải để test offline.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

import yaml

from app.config import BASE_DIR

logger = logging.getLogger(__name__)

RSS = "https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={gl}:{hl}"


def load_news_config(path: Optional[Path] = None) -> dict:
    p = path or (BASE_DIR / "config" / "news.yaml")
    if not p.exists():
        return {"queries": [], "limit": 12, "hl": "vi", "gl": "VN"}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _clean(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")  # bỏ HTML thô trong description
    return re.sub(r"\s+", " ", text).strip()


def parse_google_news_rss(xml: str, category: str = "") -> list[dict]:
    """Trích danh sách tin {published_at, title, summary, url, source, category}."""
    from lxml import etree

    try:
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    except Exception as exc:  # noqa: BLE001
        logger.error("RSS lỗi: %s", exc)
        return []

    out: list[dict] = []
    for item in root.findall(".//item"):
        title = _clean(_text(item, "title"))
        link = _text(item, "link")
        if not title or not link:
            continue
        desc = _clean(_text(item, "description"))
        # Google News description thường lặp tiêu đề → tóm tắt 1-2 câu
        summary = desc[:200]
        source = _text(item, "{http://www.w3.org/2005/Atom}source") or \
            _child_text(item, "source")
        out.append({
            "published_at": _rss_date(_text(item, "pubDate")),
            "title": title, "summary": summary, "url": link,
            "source": source or "Google News", "category": category,
        })
    return out


def _text(el, tag: str) -> str:
    node = el.find(tag)
    return (node.text or "").strip() if node is not None and node.text else ""


def _child_text(el, tag: str) -> str:
    for c in el:
        if c.tag.endswith(tag):
            return (c.text or "").strip()
    return ""


def _rss_date(s: str) -> str:
    # "Wed, 10 Jun 2026 08:00:00 GMT" → 2026-06-10
    from datetime import datetime

    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except (ValueError, TypeError):
            continue
    return ""


def collect_news(limit: Optional[int] = None) -> list[dict]:
    """Thu thập tin từ mọi truy vấn, khử trùng lặp theo URL. Fail-soft."""
    import httpx

    cfg = load_news_config()
    limit = limit or int(cfg.get("limit", 12))
    hl, gl = cfg.get("hl", "vi"), cfg.get("gl", "VN")

    seen: set[str] = set()
    news: list[dict] = []
    for query in cfg.get("queries", []):
        url = RSS.format(q=quote_plus(query["q"]), hl=hl, gl=gl)
        try:
            r = httpx.get(url, timeout=20, follow_redirects=True)
            r.raise_for_status()
            for item in parse_google_news_rss(r.text, query.get("category", "")):
                if item["url"] in seen:
                    continue
                seen.add(item["url"])
                news.append(item)
        except Exception as exc:  # noqa: BLE001 — 1 truy vấn lỗi không dừng cả lượt
            logger.warning("Tin '%s' lỗi: %s", query.get("q"), exc)

    news.sort(key=lambda n: n["published_at"], reverse=True)
    return news[:limit]
