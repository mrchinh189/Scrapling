"""Nguồn dữ liệu cho lõi phân tích.

Mặc định đọc fixtures (offline, không cần key). Khi có DB thật, có thể thay
`load_price_master` bằng truy vấn Supabase mà không đổi phần phân tích.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Optional

from app.config import BASE_DIR, DATA_DIR
from app.analytics.units import to_usd_per_ton

FIXTURES = BASE_DIR / "fixtures"


def _pick(name: str) -> Path:
    """Ưu tiên dữ liệu THẬT đã thu thập (data/) rồi mới đến fixtures mẫu."""
    live = DATA_DIR / name
    return live if live.exists() else (FIXTURES / name)


def load_price_master(path: Optional[Path] = None) -> list[dict]:
    p = path or _pick("price_master.csv")
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["raw_price"] = float(r["raw_price"])
    return rows


def load_fx(path: Optional[Path] = None) -> list[dict]:
    p = path or _pick("fx.csv")
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["usd_vnd"] = float(r["usd_vnd"])
        r["rmb_vnd"] = float(r["rmb_vnd"])
    return rows


def latest_fx(fx: Optional[list[dict]] = None) -> dict:
    fx = fx if fx is not None else load_fx()
    if not fx:
        return {"usd_vnd": 25450.0, "rmb_vnd": 3520.0, "date": ""}
    return sorted(fx, key=lambda r: r["date"])[-1]


def latest_date(rows: list[dict]) -> str:
    return max((r["date"] for r in rows), default="")


def latest_quotes(product: str, rows: Optional[list[dict]] = None) -> list[dict]:
    """Báo giá MỚI NHẤT của mỗi (region, source, payment_term) cho 1 NVL."""
    rows = rows if rows is not None else load_price_master()
    groups: dict[tuple, dict] = {}
    for r in rows:
        if r["product"] != product:
            continue
        key = (r["region"], r["source"], r["payment_term"])
        if key not in groups or r["date"] > groups[key]["date"]:
            groups[key] = r
    return list(groups.values())


def normalized_series(
    product: str,
    rows: Optional[list[dict]] = None,
    fx: Optional[list[dict]] = None,
) -> list[tuple[str, float]]:
    """Chuỗi thời gian (date, giá_đại_diện) cho forecast/spreads.

    Lấy 1 nguồn đại diện (region đầu tiên theo thứ tự chữ cái) và quy về USD/tấn
    (hoặc giữ USD/thùng cho feedstock dạng bbl). Trả [(date, value), ...] tăng dần.
    """
    rows = rows if rows is not None else load_price_master()
    fx = fx if fx is not None else load_fx()
    fx_by_date = {r["date"]: r for r in fx}

    prod_rows = [r for r in rows if r["product"] == product]
    if not prod_rows:
        return []
    # Chọn nguồn đại diện ổn định: (region, source) nhỏ nhất
    rep_key = sorted({(r["region"], r["source"]) for r in prod_rows})[0]
    series = []
    for r in sorted(prod_rows, key=lambda x: x["date"]):
        if (r["region"], r["source"]) != rep_key:
            continue
        unit = r["raw_unit"].lower()
        if unit == "usd_per_bbl":
            val = r["raw_price"]
        else:
            f = fx_by_date.get(r["date"], latest_fx(fx))
            val = to_usd_per_ton(r["raw_price"], r["raw_unit"], f["usd_vnd"], f["rmb_vnd"])
        if val is not None:
            series.append((r["date"], round(val, 2)))
    return series


def load_news(path: Optional[Path] = None) -> list[dict]:
    """Tin tức (data/news.csv thật, ngược lại fixtures/news.csv mẫu)."""
    p = path or _pick("news.csv")
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def all_products(rows: Optional[list[dict]] = None) -> list[str]:
    rows = rows if rows is not None else load_price_master()
    seen = []
    for r in rows:
        if r["product"] not in seen:
            seen.append(r["product"])
    return seen
