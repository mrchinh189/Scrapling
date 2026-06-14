"""Kiểm soát chất lượng (QC): phát hiện biến động bất thường → flag review.

Nguyên tắc spec: bản ghi nhảy > ngưỡng → ĐÁNH DẤU để soát, KHÔNG xoá dữ liệu.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app import configs
from app.analytics import datasource as ds


def check_jumps(rows=None, fx=None) -> list[dict]:
    """Trả danh sách cảnh báo QC {at, kind, product, detail} cho biến động > ngưỡng."""
    rows = rows if rows is not None else ds.load_price_master()
    fx = fx if fx is not None else ds.load_fx()
    jump = float(configs.thresholds().get("qc", {}).get("jump_pct", 10.0))
    now = datetime.now(timezone.utc).isoformat()

    audit: list[dict] = []
    for product in ds.all_products(rows):
        series = ds.normalized_series(product, rows, fx)
        for i in range(1, len(series)):
            prev, cur = series[i - 1][1], series[i][1]
            if prev == 0:
                continue
            pct = (cur - prev) / prev * 100
            if abs(pct) >= jump:
                audit.append({
                    "at": now, "kind": "price_jump", "product": product,
                    "detail": f"{product} {series[i][0]}: {pct:+.1f}% "
                              f"({prev:,.0f} → {cur:,.0f}) — cần soát.",
                })
    return audit
