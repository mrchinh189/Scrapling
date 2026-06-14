"""Độ tươi dữ liệu 🟢🟡🔴 tính từ NGÀY GIÁ (date), không phải giờ chạy."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional


def _parse(d: str) -> Optional[date]:
    try:
        return datetime.strptime(d[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def freshness(price_date: str, today: Optional[date] = None) -> str:
    """🟢 ≤7 ngày · 🟡 ≤30 ngày · 🔴 >30 ngày · ⚪ không rõ ngày."""
    d = _parse(price_date)
    if d is None:
        return "⚪"
    today = today or date.today()
    age = (today - d).days
    if age <= 7:
        return "🟢"
    if age <= 30:
        return "🟡"
    return "🔴"
