"""Engine quy đổi LANDED COST + AT-SIGHT TƯƠNG ĐƯƠNG (mục lõi ④).

Cho mỗi NVL, gom các báo giá ở nhiều nguồn/khu vực/điều khoản thanh toán,
quy về VND/kg landed và at-sight tương đương để XẾP HẠNG công bằng.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app import configs
from app.analytics.units import to_usd_per_ton


@dataclass
class LandedRow:
    product: str
    region: str
    price_type: str
    payment_term: str
    raw_price: float
    raw_unit: str
    source: str
    date: str
    usd_per_ton: Optional[float] = None
    landed_vnd_kg: Optional[float] = None
    usance_benefit: Optional[float] = None
    at_sight_equiv: Optional[float] = None
    is_best: bool = False


def _term_days(term: str, cfg: dict) -> int:
    days_map = cfg.get("payment_term_days", {})
    if term in days_map:
        return int(days_map[term])
    # Suy số ngày từ chuỗi (vd "L/C 90" -> 90), mặc định 0 (at sight)
    digits = "".join(ch for ch in term if ch.isdigit())
    return int(digits) if digits else 0


def _freight_pct(region: str, cfg: dict) -> float:
    fi = cfg.get("freight_insurance_pct", {})
    return float(fi.get(region, fi.get("default", 0.05)))


def _domestic_cost(region: str, cfg: dict) -> float:
    dc = cfg.get("domestic_cost_vnd_kg", {})
    return float(dc.get(region, dc.get("default", 0)))


def compute_landed(
    quotes: list[dict],
    usd_vnd: float,
    rmb_vnd: float,
    duty_key: Optional[str],
) -> list[LandedRow]:
    """Tính landed + at-sight cho danh sách báo giá CÙNG một NVL.

    Mỗi quote: {region, price_type, payment_term, raw_price, raw_unit, source, date}
    Công thức (kinh tế chuẩn):
      cif         = usd_per_ton × (1 + cước+bảo hiểm%)
      landed_usd  = cif × (1 + thuế_NK%)
      landed_vnd_kg = landed_usd × fx / 1000 + phí nội địa (VND/kg)
      usance      = landed_vnd_kg × lãi%/năm × số_ngày_nợ / 365
      at_sight    = landed_vnd_kg − usance   (con số xếp hạng công bằng)
    """
    cfg = configs.landed_config()
    interest = float(cfg.get("interest_pct_year", 0.065))
    duty = float(cfg.get("duty_pct", {}).get(duty_key, 0.0)) if duty_key else 0.0

    rows: list[LandedRow] = []
    for q in quotes:
        row = LandedRow(
            product=q.get("product", ""),
            region=q.get("region", "default"),
            price_type=q.get("price_type", ""),
            payment_term=q.get("payment_term", "at_sight"),
            raw_price=float(q["raw_price"]),
            raw_unit=q.get("raw_unit", "usd_per_ton"),
            source=q.get("source", ""),
            date=q.get("date", ""),
        )
        usd_ton = to_usd_per_ton(row.raw_price, row.raw_unit, usd_vnd, rmb_vnd)
        row.usd_per_ton = round(usd_ton, 2) if usd_ton is not None else None
        if usd_ton is not None:
            freight = _freight_pct(row.region, cfg)
            cif = usd_ton * (1 + freight)
            landed_usd = cif * (1 + duty)
            landed_vnd_kg = landed_usd * usd_vnd / 1000.0 + _domestic_cost(row.region, cfg)
            days = _term_days(row.payment_term, cfg)
            usance = landed_vnd_kg * interest * days / 365.0
            row.landed_vnd_kg = round(landed_vnd_kg, 0)
            row.usance_benefit = round(usance, 0)
            row.at_sight_equiv = round(landed_vnd_kg - usance, 0)
        rows.append(row)

    # Xếp hạng tăng dần theo at-sight; đánh dấu nguồn tốt nhất
    ranked = [r for r in rows if r.at_sight_equiv is not None]
    ranked.sort(key=lambda r: r.at_sight_equiv)
    if ranked:
        ranked[0].is_best = True
    return rows


def landed_spread(rows: list[LandedRow]) -> Optional[float]:
    """Chênh lệch max−min của at-sight (đ/kg) trong một NVL."""
    vals = [r.at_sight_equiv for r in rows if r.at_sight_equiv is not None]
    if len(vals) < 2:
        return None
    return round(max(vals) - min(vals), 0)
