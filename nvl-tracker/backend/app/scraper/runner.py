"""Crawl giá NVL từ các nguồn đã cấu hình (dùng Scrapling)."""

from __future__ import annotations

import logging
from typing import Optional

from app.models import PriceRecord, SourceConfig
from app.scraper.price_parser import parse_price

logger = logging.getLogger(__name__)


def _fetch_html(source: SourceConfig) -> str:
    """Tải HTML của một nguồn bằng Scrapling.

    Import ở trong hàm để phần parse có thể test mà không cần cài đặt
    đầy đủ bộ fetcher (curl_cffi / playwright).
    """
    from scrapling.fetchers import Fetcher, StealthyFetcher

    if source.fetcher == "stealthy":
        page = StealthyFetcher.fetch(source.url, headless=True, network_idle=True)
    else:
        page = Fetcher.get(source.url, stealthy_headers=True, timeout=30)
    if page.status >= 400:
        raise RuntimeError(f"HTTP {page.status} khi tải {source.url}")
    return page.body if hasattr(page, "body") else str(page)


def extract_price(html: str, source: SourceConfig) -> Optional[PriceRecord]:
    """Trích một bản ghi giá từ HTML theo cấu hình nguồn.

    Tách riêng khỏi phần tải để dễ kiểm thử với HTML cố định.
    """
    from scrapling.parser import Selector

    sel = Selector(content=html)

    raw_text = ""
    if source.price_selector:
        found = sel.css(source.price_selector)
        if found:
            raw_text = found[0].text or ""
    if not raw_text:
        logger.warning("Không tìm thấy giá cho %s (%s)", source.code, source.url)
        return None

    price = parse_price(raw_text, source.price_regex)
    if price is None:
        logger.warning("Không tách được số từ '%s' cho %s", raw_text, source.code)
        return None

    return PriceRecord(
        material_code=source.code,
        material_name=source.name,
        price=price,
        unit=source.unit,
        source=source.url.split("/")[2] if "//" in source.url else source.url,
        source_url=source.url,
        raw_text=raw_text.strip()[:200],
    )


def scrape_source(source: SourceConfig) -> PriceRecord:
    """Tải và trích giá cho một nguồn. Ném lỗi nếu thất bại."""
    html = _fetch_html(source)
    record = extract_price(html, source)
    if record is None:
        raise RuntimeError(f"Không trích được giá cho nguồn {source.code}")
    return record


def scrape_all(sources: list[SourceConfig]) -> tuple[list[PriceRecord], list[str]]:
    """Crawl toàn bộ nguồn. Trả về (records, errors)."""
    records: list[PriceRecord] = []
    errors: list[str] = []
    for source in sources:
        try:
            records.append(scrape_source(source))
            logger.info("Đã lấy giá %s = %s", source.code, records[-1].price)
        except Exception as exc:  # noqa: BLE001 — gom lỗi từng nguồn, không dừng cả lượt
            msg = f"{source.code}: {exc}"
            errors.append(msg)
            logger.error("Lỗi crawl %s", msg)
    return records, errors
