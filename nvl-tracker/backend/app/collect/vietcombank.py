"""Collector tỷ giá Vietcombank (USD/VND, CNY/VND) từ XML công khai. Fail-soft."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

VCB_URL = "https://portal.vietcombank.com.vn/UserControls/TVPortal.TyGia/pXML.aspx?b=10"


def parse_vcb_xml(xml: str) -> Optional[dict]:
    """Trích {date, usd_vnd, rmb_vnd} từ XML Vietcombank (testable).

    Dùng lxml (đã là dep của Scrapling) — Scrapling tối ưu cho HTML, XML tỷ giá
    parse bằng lxml.etree gọn hơn.
    """
    from lxml import etree

    try:
        root = etree.fromstring(xml.encode("utf-8") if isinstance(xml, str) else xml)
    except Exception as exc:  # noqa: BLE001
        logger.error("XML Vietcombank lỗi: %s", exc)
        return None

    usd = rmb = None
    for ex in root.findall(".//Exrate"):
        code = (ex.get("CurrencyCode") or "").upper()
        transfer = ex.get("Transfer") or ex.get("Sell") or ""
        val = _num(transfer)
        if code == "USD":
            usd = val
        elif code == "CNY":
            rmb = val

    date_node = root.find(".//DateTime")
    date_ = ""
    if date_node is not None and date_node.text:
        date_ = _vcb_date(date_node.text)

    if usd is None:
        return None
    return {"date": date_, "usd_vnd": usd, "rmb_vnd": rmb or round(usd / 7.2, 1)}


def _num(s: str) -> Optional[float]:
    s = (s or "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return None


def _vcb_date(s: str) -> str:
    # Vietcombank: "6/14/2026 4:00:00 PM" hoặc tương tự → YYYY-MM-DD
    import re
    from datetime import datetime

    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m:
        mo, d, y = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return datetime.now().date().isoformat()


def collect_vietcombank() -> Optional[dict]:
    """Trả {date, usd_vnd, rmb_vnd} hoặc None (fail-soft)."""
    try:
        from app.collect.base import fetch_text

        return parse_vcb_xml(fetch_text(VCB_URL))
    except Exception as exc:  # noqa: BLE001
        logger.error("Collector Vietcombank lỗi: %s", exc)
        return None
