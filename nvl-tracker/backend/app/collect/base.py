"""Tiện ích chung cho collectors: tải trang bằng Scrapling, chuẩn hoá bản ghi."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


def has_env(*keys: str) -> bool:
    """True nếu MỌI biến môi trường đều có giá trị (để fail-soft khi thiếu key)."""
    return all(os.environ.get(k) for k in keys)


def today_str(tz: str = "Asia/Ho_Chi_Minh") -> str:
    try:
        from zoneinfo import ZoneInfo

        return date.today().isoformat() if not tz else \
            __import__("datetime").datetime.now(ZoneInfo(tz)).date().isoformat()
    except Exception:  # noqa: BLE001
        return date.today().isoformat()


@dataclass
class CollectResult:
    source: str
    rows: list[dict] = field(default_factory=list)
    ok: bool = True
    error: str = ""


def fetch_html(url: str, fetcher: str = "static", timeout: int = 30) -> str:
    """Tải HTML bằng Scrapling. Import trễ để test parse không cần bộ fetcher.

    fetcher='stealthy' dùng trình duyệt ẩn danh (trang chặn bot / render JS).
    """
    from scrapling.fetchers import Fetcher, StealthyFetcher

    if fetcher == "stealthy":
        page = StealthyFetcher.fetch(url, headless=True, network_idle=True)
    else:
        page = Fetcher.get(url, stealthy_headers=True, timeout=timeout)
    status = getattr(page, "status", 200)
    if status and status >= 400:
        raise RuntimeError(f"HTTP {status}")
    return page.body if hasattr(page, "body") else str(page)


def fetch_text(url: str, timeout: int = 30) -> str:
    """Tải nội dung text/XML/RSS — ưu tiên Scrapling (stealthy headers, ít bị chặn),
    fallback httpx. Dùng cho Vietcombank XML, Google News RSS."""
    try:
        from scrapling.fetchers import Fetcher

        page = Fetcher.get(url, stealthy_headers=True, timeout=timeout)
        if getattr(page, "status", 200) < 400:
            return page.body if hasattr(page, "body") else str(page)
        raise RuntimeError(f"HTTP {page.status}")
    except ImportError:
        pass  # bộ fetchers chưa cài → dùng httpx
    import httpx

    r = httpx.get(url, timeout=timeout, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0 (compatible; NVLBot/1.0)"})
    r.raise_for_status()
    return r.text


def make_row(
    *, date_: str, product: str, region: str, price_type: str,
    payment_term: str, raw_price: float, raw_unit: str, source: str,
) -> dict:
    return {
        "date": date_, "product": product, "region": region,
        "price_type": price_type, "payment_term": payment_term,
        "raw_price": raw_price, "raw_unit": raw_unit, "source": source,
    }
