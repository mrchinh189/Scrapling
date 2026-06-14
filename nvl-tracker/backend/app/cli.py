"""CLI tiện ích.

  python -m app.cli run                # chạy cập nhật ngay
  python -m app.cli prices             # in bảng giá mới nhất
  python -m app.cli inspect <url> [css]  # dò HTML/selector của một trang
"""

from __future__ import annotations

import logging
import sys


def _run() -> None:
    from app.service import run_update

    result = run_update(send_telegram=False, make_report=True)
    print(f"Run {result.run_id}: {result.status} — {len(result.records)} bản ghi")
    for c in result.changes:
        pct = f"{c.change_pct:+.2f}%" if c.change_pct is not None else "n/a"
        print(f"  {c.material_code}: {c.current_price:,.0f} {c.unit} ({pct})")
    if result.docx_path:
        print(f"Báo cáo: {result.docx_path}")
    for e in result.errors:
        print(f"  [lỗi] {e}")


def _prices() -> None:
    from app.db import get_repository

    for r in get_repository().latest_prices():
        print(f"{r['material_code']:12} {float(r['price']):>15,.0f} {r.get('unit','')}")


def _inspect(url: str, css: str | None) -> None:
    from scrapling.fetchers import Fetcher

    page = Fetcher.get(url, stealthy_headers=True, timeout=30)
    print(f"HTTP {page.status} — {len(page.body)} bytes")
    if css:
        found = page.css(css)
        print(f"Selector '{css}' khớp {len(found)} phần tử:")
        for el in found[:5]:
            print("  ->", repr(el.text.strip()[:120]))
    else:
        print("Gợi ý: truyền thêm CSS selector để thử trích. Vd:")
        print(f"  python -m app.cli inspect {url} '.price'")


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    cmd = args[0]
    if cmd == "run":
        _run()
    elif cmd == "prices":
        _prices()
    elif cmd == "inspect" and len(args) >= 2:
        _inspect(args[1], args[2] if len(args) > 2 else None)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
