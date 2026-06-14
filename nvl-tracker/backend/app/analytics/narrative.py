"""Sinh narrative 4 đoạn (mục ④): Bức tranh · Vì sao · Hệ quả EUP · Khuyến nghị.

Mặc định template từ số liệu; nếu có ANTHROPIC_API_KEY thì Claude tinh chỉnh câu chữ
(số liệu KHÔNG đổi). Kết quả ghi vào view-model để DOCX/Web/Telegram đọc chung.
"""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


def build_narrative(kpis: list[dict], spreads: list[dict], alerts: list[dict]) -> dict:
    """Trả {current, why, impact, recommendation, combined_md}."""
    ups = [k for k in kpis if k.get("change_pct") and k["change_pct"] > 0]
    downs = [k for k in kpis if k.get("change_pct") and k["change_pct"] < 0]
    ups.sort(key=lambda k: k["change_pct"], reverse=True)
    downs.sort(key=lambda k: k["change_pct"])

    top_up = ups[0] if ups else None
    top_down = downs[0] if downs else None
    naph_eth = next((s for s in spreads if s["name"] == "Naphtha–Ethylene"), None)

    current = (
        f"Theo dõi {len(kpis)} nhóm NVL: {len(ups)} tăng, {len(downs)} giảm. "
        + (f"Tăng mạnh nhất là {top_up['product']} ({top_up['change_pct']:+.1f}%). " if top_up else "")
        + (f"Giảm mạnh nhất là {top_down['product']} ({top_down['change_pct']:+.1f}%). " if top_down else "")
    )
    why = (
        "Nhựa nền (PP/PE) chịu ảnh hưởng chuỗi truyền dẫn dầu Brent → naphtha → "
        "olefin với độ trễ ~5 tuần; "
        + (f"spread Naphtha–Ethylene hiện {naph_eth['value']} {naph_eth['unit']} "
           f"({naph_eth['signal']}). " if naph_eth else "")
        + "Phụ gia (TiO₂, stearic, wax) theo nhịp cost-push riêng (axit sulfuric, dầu cọ)."
    )
    impact = (
        "NVL chiếm 70–85% giá vốn masterbatch nên mỗi 1% mua tốt ≈ +1% biên lợi nhuận. "
        + ("Phân kỳ resin▼ vs phụ gia▲ đòi hỏi chiến lược mua khác nhau theo nhóm."
           if ups and downs else "Xu hướng giá tương đối đồng pha giữa các nhóm.")
    )
    recs = [a["recommendation"].lstrip("→ ").strip() for a in alerts[:3]]
    recommendation = "Khuyến nghị nhanh: " + (
        "; ".join(recs) if recs else "duy trì theo dõi, chưa có tín hiệu hành động khẩn."
    )

    out = {"current": current, "why": why, "impact": impact, "recommendation": recommendation}
    out["combined_md"] = _to_md(out)

    settings = get_settings()
    if settings.has_anthropic:
        refined = _refine_with_claude(out)
        if refined:
            out["combined_md"] = refined
    return out


def _to_md(n: dict) -> str:
    return (
        f"**Bức tranh hiện tại.** {n['current']}\n\n"
        f"**Vì sao.** {n['why']}\n\n"
        f"**Hệ quả với EUP.** {n['impact']}\n\n"
        f"**{n['recommendation']}**"
    )


def _refine_with_claude(n: dict) -> str | None:
    settings = get_settings()
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        prompt = (
            "Biên tập lại 4 đoạn phân tích giá NVL sau cho mạch lạc, chuyên nghiệp, "
            "GIỮ NGUYÊN mọi con số và sự kiện, không thêm số mới. Trả Markdown, giữ 4 đề mục in đậm.\n\n"
            + _to_md(n)
        )
        with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=2000,
            thinking={"type": "adaptive"},
            output_config={"effort": settings.anthropic_effort},
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            msg = stream.get_final_message()
        text = "".join(b.text for b in msg.content if b.type == "text")
        return text or None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Claude tinh chỉnh narrative lỗi: %s — dùng template", exc)
        return None
