"""Backfill lịch sử giá từ FRED (3–5 năm nền) để forecast tin cậy hơn. Fail-soft.

Tách `parse_fred_observations` (thuần) khỏi phần tải để test offline.
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import yaml

from app.collect.base import make_row
from app.config import BASE_DIR

logger = logging.getLogger(__name__)

FRED_URL = "https://api.stlouisfed.org/fred/series/observations"


def load_history_config(path: Optional[Path] = None) -> dict:
    p = path or (BASE_DIR / "config" / "history.yaml")
    if not p.exists():
        return {"fred_series": [], "years": 3}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def parse_fred_observations(payload: dict, cfg: dict) -> list[dict]:
    """Trích bản ghi từ JSON FRED → các dòng price_master (testable)."""
    obs = (payload or {}).get("observations", [])
    rows = []
    for o in obs:
        val = o.get("value")
        if val in (None, "", "."):  # FRED dùng "." cho giá trị thiếu
            continue
        try:
            price = float(val)
        except ValueError:
            continue
        rows.append(make_row(
            date_=o.get("date", ""), product=cfg["product"],
            region=cfg.get("region", "GLOBAL"), price_type=cfg.get("price_type", "spot"),
            payment_term="at_sight", raw_price=price,
            raw_unit=cfg.get("raw_unit", "usd_per_ton"), source=cfg.get("source", "FRED"),
        ))
    return rows


def collect_history(years: Optional[int] = None) -> list[dict]:
    """Nạp các chuỗi FRED. Trả danh sách dòng price_master. Fail-soft."""
    key = os.environ.get("FRED_API_KEY")
    if not key:
        logger.info("Thiếu FRED_API_KEY — bỏ qua backfill lịch sử (fail-soft).")
        return []

    import httpx

    cfg = load_history_config()
    years = years or int(cfg.get("years", 3))
    start = (date.today() - timedelta(days=365 * years)).isoformat()

    all_rows: list[dict] = []
    for series in cfg.get("fred_series", []):
        try:
            r = httpx.get(FRED_URL, timeout=30, params={
                "series_id": series["series_id"], "api_key": key,
                "file_type": "json", "observation_start": start,
            })
            r.raise_for_status()
            rows = parse_fred_observations(r.json(), series)
            all_rows.extend(rows)
            logger.info("FRED %s: +%d điểm", series["series_id"], len(rows))
        except Exception as exc:  # noqa: BLE001 — 1 chuỗi lỗi không dừng cả lượt
            logger.warning("FRED %s lỗi: %s", series.get("series_id"), exc)
    return all_rows
