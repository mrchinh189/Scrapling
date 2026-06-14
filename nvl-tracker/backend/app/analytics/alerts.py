"""Sinh thẻ cảnh báo & đề xuất hành động (mục ⑦/⑧).

severity ∈ {MUA, THEO_DÕI, PHÂN_KỲ, CHỜ}. Mỗi thẻ luôn kèm "→ Đề xuất".
"""

from __future__ import annotations

from typing import Optional

from app import configs

SEVERITY_ICON = {"MUA": "🟢", "THEO_DÕI": "🔵", "PHÂN_KỲ": "🟠", "CHỜ": "⚪"}


def build_alerts(
    landed_by_product: dict[str, list],
    spreads: list[dict],
    forecasts: dict,
    kpis: list[dict],
) -> list[dict]:
    """Trả danh sách thẻ {severity, title, detail, recommendation}."""
    th = configs.thresholds().get("alerts", {})
    cards: list[dict] = []

    # 1) Nguồn at-sight tốt nhất cho từng NVL chính
    for product, rows in landed_by_product.items():
        best = next((r for r in rows if getattr(r, "is_best", False)), None)
        if best:
            cards.append({
                "severity": "THEO_DÕI",
                "title": f"{product}: nguồn tốt nhất — {best.source} ({best.region})",
                "detail": f"At-sight ~{best.at_sight_equiv:,.0f} đ/kg, "
                          f"thanh toán {best.payment_term}.",
                "recommendation": f"→ Ưu tiên chào giá từ {best.source}; "
                                  f"đàm phán điều khoản trả chậm để tối ưu vốn.",
            })

    # 2) Spread naphtha–ethylene thấp → resin tạo đáy
    for s in spreads:
        if s["name"] == "Naphtha–Ethylene" and "đáy" in s.get("signal", ""):
            cards.append({
                "severity": "CHỜ",
                "title": "Resin có thể đang tạo đáy",
                "detail": f"Spread {s['name']} = {s['value']} {s['unit']} (dưới ngưỡng).",
                "recommendation": "→ Chưa vội chốt dài hạn; theo dõi 1–2 tuần để bắt đáy.",
            })

    # 3) Phân kỳ: phụ gia tăng khi resin giảm
    ups = [k for k in kpis if k.get("change_pct") and k["change_pct"] > 0
           and k.get("family") == "additive"]
    downs = [k for k in kpis if k.get("change_pct") and k["change_pct"] < 0
             and k.get("family") == "resin"]
    if ups and downs:
        names = ", ".join(k["product"] for k in ups[:3])
        cards.append({
            "severity": "PHÂN_KỲ",
            "title": "Phân kỳ resin▼ vs phụ gia▲",
            "detail": f"Phụ gia tăng ({names}) trong khi nhựa nền hạ nhiệt.",
            "recommendation": "→ Cân nhắc chốt sớm phụ gia đang tăng; "
                              "giãn mua resin để tận dụng đà giảm.",
        })

    # 4) Forecast giảm → tín hiệu chờ mua
    drop = float(th.get("forecast_drop_pct", 3.0))
    for product, fc in forecasts.items():
        if not fc.points:
            continue
        last_actual = fc.points[0]["yhat"]
        end = fc.points[-1]["yhat"]
        if last_actual and (end - last_actual) / last_actual * 100 <= -drop:
            cards.append({
                "severity": "CHỜ",
                "title": f"{product}: dự báo còn giảm",
                "detail": f"Dự báo {fc.horizon} tuần giảm ~"
                          f"{(end - last_actual) / last_actual * 100:.1f}% "
                          f"(model {fc.model}, tin cậy {fc.confidence}).",
                "recommendation": "→ Mua cầm chừng theo nhu cầu; chờ vùng giá thấp hơn.",
            })

    # 5) Biến động tuần mạnh
    jump = float(th.get("weekly_jump_pct", 5.0))
    for k in kpis:
        if k.get("change_pct") and abs(k["change_pct"]) >= jump:
            sev = "MUA" if k["change_pct"] < 0 else "THEO_DÕI"
            cards.append({
                "severity": sev,
                "title": f"{k['product']}: biến động mạnh {k['change_pct']:+.1f}%",
                "detail": f"Giá {k['product']} thay đổi đột biến tuần này.",
                "recommendation": "→ Rà lại hợp đồng/khối lượng mua trong tuần.",
            })

    return cards
