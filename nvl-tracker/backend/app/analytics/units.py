"""Chuẩn hoá đơn vị giá về USD/tấn (feedstock USD/thùng giữ riêng)."""

from __future__ import annotations

from typing import Optional

LB_PER_TON = 2204.62  # 1 tấn = 2204.62 lb


def to_usd_per_ton(
    raw_price: float,
    raw_unit: str,
    usd_vnd: Optional[float] = None,
    rmb_vnd: Optional[float] = None,
) -> Optional[float]:
    """Quy giá thô về USD/tấn.

    - cents_per_lb : ¢/lb × 22.0462
    - rmb_per_ton  : ÷ tỉ giá RMB→USD (= rmb_vnd / usd_vnd)
    - usd_per_ton  : giữ nguyên
    - usd_per_bbl  : trả None (feedstock — không quy landed)
    """
    unit = raw_unit.strip().lower()
    if unit == "usd_per_ton":
        return raw_price
    if unit == "cents_per_lb":
        return raw_price * LB_PER_TON / 100.0
    if unit == "rmb_per_ton":
        if not usd_vnd or not rmb_vnd:
            return None
        rmb_to_usd = rmb_vnd / usd_vnd
        return raw_price * rmb_to_usd
    if unit == "usd_per_bbl":
        return None  # feedstock, không landed
    return None
