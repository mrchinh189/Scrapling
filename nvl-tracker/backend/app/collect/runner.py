"""Điều phối toàn bộ collectors → ghi data/price_master.csv + data/fx.csv (dedup).

Fail-soft tuyệt đối: nguồn nào thiếu key / bị chặn / lỗi parse → SKIP, ghi log,
KHÔNG dừng cả lượt. Trả về bảng tóm tắt (kiểm soát nguồn & chi phí).
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR
from app.collect.base import CollectResult

logger = logging.getLogger(__name__)

PRICE_COLS = ["date", "product", "region", "price_type", "payment_term",
              "raw_price", "raw_unit", "source"]
FX_COLS = ["date", "usd_vnd", "rmb_vnd"]
NEWS_COLS = ["published_at", "title", "summary", "url", "source", "category"]

PRICE_CSV = DATA_DIR / "price_master.csv"
FX_CSV = DATA_DIR / "fx.csv"
NEWS_CSV = DATA_DIR / "news.csv"


def _merge_csv(path: Path, cols: list[str], new_rows: list[dict], key) -> int:
    """Gộp bản ghi mới vào CSV, khử trùng lặp theo `key`. Trả số dòng thêm/ghi đè."""
    existing: dict = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing[key(r)] = r
    added = 0
    for r in new_rows:
        k = key(r)
        if k not in existing:
            added += 1
        existing[key({c: str(r.get(c, "")) for c in cols})] = {c: r.get(c, "") for c in cols}
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in existing.values():
            w.writerow({c: r.get(c, "") for c in cols})
    return added


def collect_all(run_web: bool = True) -> dict:
    """Chạy mọi collector, ghi dữ liệu thật, trả tóm tắt."""
    from app.collect.eia import collect_eia
    from app.collect.vietcombank import collect_vietcombank
    from app.collect.web import collect_web

    results: list[CollectResult] = []

    # Tầng API free
    results.append(collect_eia())
    # Tầng web (Scrapling)
    if run_web:
        results.extend(collect_web())

    price_rows = [r for res in results for r in res.rows]
    added_prices = _merge_csv(
        PRICE_CSV, PRICE_COLS, price_rows,
        key=lambda r: (r["date"], r["product"], r["region"], r["source"]),
    ) if price_rows else 0

    # Tỷ giá
    fx = collect_vietcombank()
    added_fx = 0
    if fx:
        added_fx = _merge_csv(FX_CSV, FX_COLS, [fx], key=lambda r: (r["date"],))

    # Tin tức
    added_news = 0
    try:
        from app.collect.news import collect_news

        news = collect_news()
        if news:
            added_news = _merge_csv(NEWS_CSV, NEWS_COLS, news, key=lambda r: (r["url"],))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Thu thập tin lỗi: %s", exc)

    summary = {
        "sources_ok": [r.source for r in results if r.ok],
        "sources_failed": [{"source": r.source, "error": r.error}
                           for r in results if not r.ok],
        "prices_added": added_prices,
        "fx_added": added_fx,
        "news_added": added_news,
        "price_csv": str(PRICE_CSV) if price_rows else None,
    }
    logger.info("Collect xong: +%d giá, +%d fx, +%d tin, %d nguồn lỗi",
                added_prices, added_fx, added_news, len(summary["sources_failed"]))
    return summary
