"""Collector EIA — giá dầu Brent (RBRTE) qua API free. Fail-soft khi thiếu EIA_KEY."""

from __future__ import annotations

import logging
import os
from typing import Optional

from app.collect.base import CollectResult, make_row

logger = logging.getLogger(__name__)

EIA_URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"


def parse_eia_json(payload: dict) -> Optional[dict]:
    """Trích bản ghi Brent mới nhất từ JSON trả về của EIA (testable)."""
    data = (payload or {}).get("response", {}).get("data", [])
    if not data:
        return None
    rec = data[0]
    period = rec.get("period")
    value = rec.get("value")
    if value is None:
        return None
    return make_row(
        date_=str(period), product="BRENT", region="GLOBAL", price_type="spot",
        payment_term="at_sight", raw_price=float(value), raw_unit="usd_per_bbl",
        source="EIA",
    )


def collect_eia() -> CollectResult:
    key = os.environ.get("EIA_KEY")
    if not key:
        logger.info("Thiếu EIA_KEY — bỏ qua collector EIA (fail-soft).")
        return CollectResult("EIA", [], ok=False, error="thiếu EIA_KEY")
    try:
        import httpx

        params = {
            "api_key": key, "frequency": "daily", "data[0]": "value",
            "facets[series][]": "RBRTE", "sort[0][column]": "period",
            "sort[0][direction]": "desc", "length": 1,
        }
        r = httpx.get(EIA_URL, params=params, timeout=30)
        r.raise_for_status()
        row = parse_eia_json(r.json())
        return CollectResult("EIA", [row] if row else [], ok=bool(row))
    except Exception as exc:  # noqa: BLE001
        logger.error("Collector EIA lỗi: %s", exc)
        return CollectResult("EIA", [], ok=False, error=str(exc))
