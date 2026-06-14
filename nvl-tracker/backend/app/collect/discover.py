"""Tự gợi ý CSS selector cho ô giá từ HTML (offline — không cần mạng).

Dùng khi bạn lưu trang đích thành .html rồi nhờ dò selector, hoặc trong
`app.cli inspect` sau khi tải trang.
"""

from __future__ import annotations

import re

# Số dạng giá: 1.850.000 | 12,500 | 54.25 | 1234.56
_PRICE_RE = re.compile(r"\d{1,3}(?:[.,]\d{3})+(?:[.,]\d+)?|\d+[.,]\d+|\d{2,}")
_CUR_HINTS = ["usd", "vnd", "rmb", "cny", "$", "¢", "cent", "/lb", "/ton", "/tấn",
              "đ", "price", "giá", "eur", "bbl", "tấn"]
_CANDIDATE_TAGS = "td,span,div,b,strong,p,li,h1,h2,h3,h4"


def suggest_selectors(html: str, hint: str = "", limit: int = 10) -> list[dict]:
    """Trả danh sách gợi ý {selector, text, score} (điểm cao = khả năng là ô giá)."""
    from scrapling.parser import Selector

    sel = Selector(content=html)
    out: list[dict] = []
    seen: set[str] = set()

    for el in sel.css(_CANDIDATE_TAGS):
        text = (el.text or "").strip()
        if not text or len(text) > 40 or not _PRICE_RE.search(text):
            continue
        low = text.lower()
        score = 1 + sum(1 for k in _CUR_HINTS if k in low)
        if hint and hint.lower() in low:
            score += 3
        css = _selector_of(el)
        if not css or css in seen:
            continue
        seen.add(css)
        out.append({"selector": css, "text": text, "score": score})

    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:limit]


def _selector_of(el) -> str:
    for attr in ("generate_full_css_selector", "generate_css_selector"):
        val = getattr(el, attr, None)
        if val is None:
            continue
        try:
            return val() if callable(val) else val
        except Exception:  # noqa: BLE001
            continue
    return ""
