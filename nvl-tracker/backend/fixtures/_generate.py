"""Sinh dữ liệu mẫu (fixtures) 12 tuần để chạy/test offline.

Chạy:  python fixtures/_generate.py
Tạo:   fixtures/price_master.csv, fixtures/fx.csv
Số liệu mang tính minh hoạ (gần thực tế 2026) để demo pipeline, KHÔNG phải giá thật.
"""

from __future__ import annotations

import csv
import math
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
WEEKS = 12
START = date(2026, 3, 23)  # thứ Hai


def weeks():
    return [START + timedelta(weeks=i) for i in range(WEEKS)]


# (product, region, price_type, payment_term, raw_unit, base, trend/tuần, biên dao động, source)
SERIES = [
    # PP — nhiều nguồn để xếp hạng at-sight
    ("PP", "US", "spot", "at_sight", "cents_per_lb", 54.0, -0.2, 0.6, "ThePlasticsExchange"),
    ("PP", "CN", "futures", "L/C 90", "rmb_per_ton", 7650.0, -18.0, 40.0, "DCE"),
    ("PP", "SEA", "quote", "TT 60", "usd_per_ton", 1185.0, -3.0, 8.0, "NCC"),
    # PE
    ("PE", "US", "spot", "at_sight", "cents_per_lb", 46.0, -0.15, 0.5, "ThePlasticsExchange"),
    ("PE", "CN", "futures", "L/C 90", "rmb_per_ton", 7350.0, -12.0, 35.0, "DCE"),
    # HDPE
    ("HDPE", "US", "spot", "at_sight", "cents_per_lb", 48.0, -0.1, 0.5, "ThePlasticsExchange"),
    # PS
    ("PS", "SEA", "quote", "TT 30", "usd_per_ton", 1320.0, -2.0, 6.0, "businessanalytiq"),
    # Feedstock (chỉ báo dẫn)
    ("BRENT", "GLOBAL", "spot", "at_sight", "usd_per_bbl", 71.0, -0.4, 1.2, "EIA"),
    ("NAPHTHA", "ASIA", "spot", "at_sight", "usd_per_ton", 620.0, -2.5, 8.0, "EIA"),
    ("ETHYLENE", "ASIA", "spot", "at_sight", "usd_per_ton", 850.0, -1.5, 6.0, "businessanalytiq"),
    ("PROPYLENE", "ASIA", "spot", "at_sight", "usd_per_ton", 880.0, -2.0, 6.0, "businessanalytiq"),
    # Phụ gia — phân kỳ: TĂNG
    ("TIO2", "CN", "quote", "TT 60", "usd_per_ton", 2450.0, 12.0, 10.0, "businessanalytiq"),
    ("STEARIC", "SEA", "quote", "TT 30", "usd_per_ton", 1150.0, 6.0, 7.0, "MPOB"),
    ("ZINC_STEARATE", "CN", "quote", "TT 60", "usd_per_ton", 2050.0, 8.0, 9.0, "businessanalytiq"),
]


def osc(i: int, amp: float) -> float:
    return amp * math.sin(i * 1.1)


def main() -> None:
    HERE.mkdir(exist_ok=True)
    ws = weeks()

    with (HERE / "price_master.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "product", "region", "price_type", "payment_term",
                    "raw_price", "raw_unit", "source"])
        for (prod, region, ptype, term, unit, base, trend, amp, source) in SERIES:
            for i, d in enumerate(ws):
                price = round(base + trend * i + osc(i, amp), 2)
                w.writerow([d.isoformat(), prod, region, ptype, term, price, unit, source])

    with (HERE / "fx.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "usd_vnd", "rmb_vnd"])
        for i, d in enumerate(ws):
            w.writerow([d.isoformat(), round(25450 + 8 * i, 0), round(3520 + 1.2 * i, 1)])

    print(f"Đã sinh fixtures cho {WEEKS} tuần x {len(SERIES)} chuỗi.")


if __name__ == "__main__":
    main()
