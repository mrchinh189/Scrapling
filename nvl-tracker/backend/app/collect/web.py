"""Collector web tổng quát bằng Scrapling, cấu hình qua config/price_sources.yaml.

Tách `parse_web_source` (thuần, test bằng HTML mẫu) khỏi phần tải mạng.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

import yaml

from app.collect.base import CollectResult, fetch_html, make_row, today_str
from app.config import BASE_DIR
from app.scraper.price_parser import parse_price

logger = logging.getLogger(__name__)


def load_web_sources(path: Optional[Path] = None) -> list[dict]:
    p = path or (BASE_DIR / "config" / "price_sources.yaml")
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return [s for s in data.get("web_sources", []) if s.get("enabled")]


def parse_web_source(html: str, cfg: dict, date_: Optional[str] = None) -> Optional[dict]:
    """Trích MỘT bản ghi price_master từ HTML (testable). 3 chế độ, ưu tiên:

    1. price_selector : CSS selector tới ô giá (chính xác nhất nếu có).
    2. anchor_text    : tìm nhãn (vd "Brent"), lấy SỐ gần nhất sau nhãn (bền với layout).
    3. page_regex     : regex trên toàn văn bản trang (group 1 = số).
    """
    from scrapling.parser import Selector

    sel = Selector(content=html)
    raw_text = ""

    selector = cfg.get("price_selector", "")
    anchor = cfg.get("anchor_text", "")
    page_regex = cfg.get("page_regex", "")

    if selector and selector != "REPLACE_ME":
        found = sel.css(selector)
        if found:
            raw_text = found[0].text or ""
    elif anchor:
        text = sel.get_all_text()
        m = re.search(re.escape(anchor) + r"[^0-9\-]{0,60}([\-0-9.,]+)", text, re.IGNORECASE)
        raw_text = m.group(1) if m else ""
    elif page_regex:
        m = re.search(page_regex, sel.get_all_text(), re.IGNORECASE)
        raw_text = (m.group(1) if m and m.groups() else (m.group(0) if m else ""))

    if not raw_text:
        logger.warning("Không thấy giá: %s @ %s", cfg.get("source"), cfg.get("url"))
        return None
    price = parse_price(raw_text, cfg.get("price_regex"))
    if price is None:
        logger.warning("Không tách được số '%s' (%s)", raw_text, cfg.get("source"))
        return None

    return make_row(
        date_=date_ or cfg.get("date") or today_str(),
        product=cfg["product"], region=cfg.get("region", "default"),
        price_type=cfg.get("price_type", "spot"),
        payment_term=cfg.get("payment_term", "at_sight"),
        raw_price=price, raw_unit=cfg.get("raw_unit", "usd_per_ton"),
        source=cfg.get("source", ""),
    )


def collect_web(sources: Optional[list[dict]] = None) -> list[CollectResult]:
    """Tải & trích tất cả nguồn web đang bật. Fail-soft theo từng nguồn."""
    sources = sources if sources is not None else load_web_sources()
    results: list[CollectResult] = []
    for cfg in sources:
        name = f"{cfg.get('source')}/{cfg.get('product')}"
        try:
            html = fetch_html(cfg["url"], cfg.get("fetcher", "static"))
            row = parse_web_source(html, cfg)
            if row:
                results.append(CollectResult(name, [row]))
            else:
                results.append(CollectResult(name, [], ok=False, error="không trích được giá"))
        except Exception as exc:  # noqa: BLE001 — 1 nguồn lỗi không dừng cả lượt
            logger.error("Collector web lỗi %s: %s", name, exc)
            results.append(CollectResult(name, [], ok=False, error=str(exc)))
    return results
