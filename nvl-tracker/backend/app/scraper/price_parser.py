"""Tách giá trị số từ chuỗi text giá (hỗ trợ định dạng Việt Nam)."""

from __future__ import annotations

import re
from typing import Optional

# Cụm chữ số có thể chứa dấu . , và khoảng trắng phân tách hàng nghìn
_NUMBER_RE = re.compile(r"[-+]?\d[\d.,\s]*\d|\d")


def parse_price(text: str, pattern: Optional[str] = None) -> Optional[float]:
    """Trả về số thực từ chuỗi giá.

    Hỗ trợ các định dạng phổ biến ở VN:
      "1.850.000 VND"   -> 1850000.0   (dấu . là phân tách nghìn)
      "12.500,50"       -> 12500.5     (dấu . nghìn, , thập phân)
      "12,500"          -> 12500.0     (dấu , nghìn — kiểu Mỹ)
      "1,234.56"        -> 1234.56     (dấu , nghìn, . thập phân — kiểu Mỹ)
    """
    if text is None:
        return None
    if pattern:
        m = re.search(pattern, text)
        raw = m.group(0) if m else ""
    else:
        m = _NUMBER_RE.search(text)
        raw = m.group(0) if m else ""

    raw = raw.strip().replace(" ", "")
    if not raw:
        return None
    return _normalize_number(raw)


def _normalize_number(raw: str) -> Optional[float]:
    """Chuẩn hoá chuỗi số có cả . và , về float."""
    sign = -1.0 if raw.startswith("-") else 1.0
    raw = raw.lstrip("+-")

    has_dot = "." in raw
    has_comma = "," in raw

    if has_dot and has_comma:
        # Dấu nào xuất hiện sau cùng là dấu thập phân.
        if raw.rfind(",") > raw.rfind("."):
            # 12.500,50  -> . là nghìn, , là thập phân
            raw = raw.replace(".", "").replace(",", ".")
        else:
            # 1,234.56   -> , là nghìn, . là thập phân
            raw = raw.replace(",", "")
    elif has_comma:
        # Chỉ có dấu ,
        parts = raw.split(",")
        if len(parts[-1]) == 2 and len(parts) == 2:
            # 12,50 -> thập phân
            raw = raw.replace(",", ".")
        else:
            # 12,500 hoặc 1,234,567 -> phân tách nghìn
            raw = raw.replace(",", "")
    elif has_dot:
        parts = raw.split(".")
        # Nhiều dấu . hoặc nhóm cuối đúng 3 chữ số => phân tách nghìn
        if len(parts) > 2 or (len(parts) == 2 and len(parts[-1]) == 3):
            raw = raw.replace(".", "")
        # ngược lại giữ nguyên (12.5 = thập phân)

    try:
        return sign * float(raw)
    except ValueError:
        return None
