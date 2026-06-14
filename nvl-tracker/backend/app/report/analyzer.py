"""Sinh báo cáo phân tích giá NVL bằng Claude API (Anthropic)."""

from __future__ import annotations

import logging
from datetime import datetime

from app.config import get_settings
from app.models import PriceChange

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Bạn là chuyên gia phân tích giá nguyên vật liệu (NVL) cho doanh nghiệp sản xuất "
    "tại Việt Nam. Nhiệm vụ: viết báo cáo phân tích biến động giá ngắn gọn, chính xác, "
    "dựa HOÀN TOÀN trên số liệu được cung cấp — không bịa số. Văn phong chuyên nghiệp, "
    "tiếng Việt. Cấu trúc báo cáo bằng Markdown:\n"
    "## Tóm tắt điều hành (3-5 gạch đầu dòng)\n"
    "## Biến động nổi bật (NVL tăng/giảm mạnh nhất, kèm % và con số)\n"
    "## Phân tích & nguyên nhân khả dĩ\n"
    "## Khuyến nghị hành động (mua/chờ/đàm phán, theo mức độ ưu tiên)\n"
    "Nếu thiếu dữ liệu lịch sử, nêu rõ hạn chế thay vì suy đoán."
)


def _format_changes(changes: list[PriceChange]) -> str:
    lines = ["| NVL | Đơn vị | Giá hiện tại | Giá trước | Thay đổi | % |", "|---|---|---|---|---|---|"]
    for c in changes:
        prev = f"{c.previous_price:,.0f}" if c.previous_price is not None else "—"
        abs_ = f"{c.change_abs:+,.0f}" if c.change_abs is not None else "—"
        pct = f"{c.change_pct:+.2f}%" if c.change_pct is not None else "—"
        lines.append(
            f"| {c.material_name} ({c.material_code}) | {c.unit} | "
            f"{c.current_price:,.0f} | {prev} | {abs_} | {pct} |"
        )
    return "\n".join(lines)


def build_analysis(changes: list[PriceChange], period_label: str = "") -> str:
    """Gọi Claude để sinh nội dung phân tích (Markdown).

    Nếu chưa cấu hình ANTHROPIC_API_KEY -> trả về báo cáo cơ bản không dùng AI.
    """
    settings = get_settings()
    table = _format_changes(changes)

    if not settings.has_anthropic:
        logger.warning("Chưa có ANTHROPIC_API_KEY — sinh báo cáo cơ bản (không AI).")
        return _fallback_report(changes, table, period_label)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    user_msg = (
        f"Kỳ báo cáo: {period_label or datetime.now().strftime('%d/%m/%Y')}\n\n"
        f"Dữ liệu giá NVL (đã so sánh với lần cập nhật trước):\n\n{table}\n\n"
        "Hãy viết báo cáo phân tích theo đúng cấu trúc yêu cầu."
    )

    try:
        # Streaming để tránh timeout với output dài; adaptive thinking cho phân tích.
        with client.messages.stream(
            model=settings.anthropic_model,
            max_tokens=8000,
            system=SYSTEM_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": settings.anthropic_effort},
            messages=[{"role": "user", "content": user_msg}],
        ) as stream:
            message = stream.get_final_message()
        text = "".join(b.text for b in message.content if b.type == "text")
        return text or _fallback_report(changes, table, period_label)
    except Exception as exc:  # noqa: BLE001
        logger.error("Lỗi gọi Claude API: %s — dùng báo cáo cơ bản", exc)
        return _fallback_report(changes, table, period_label)


def _fallback_report(changes: list[PriceChange], table: str, period_label: str) -> str:
    """Báo cáo tối thiểu khi không có AI."""
    ups = [c for c in changes if c.change_pct and c.change_pct > 0]
    downs = [c for c in changes if c.change_pct and c.change_pct < 0]
    ups.sort(key=lambda c: c.change_pct, reverse=True)
    downs.sort(key=lambda c: c.change_pct)

    parts = [
        f"## Tóm tắt điều hành",
        f"- Kỳ báo cáo: {period_label or datetime.now().strftime('%d/%m/%Y')}",
        f"- Tổng số NVL theo dõi: {len(changes)}",
        f"- Số NVL tăng giá: {len(ups)} | giảm giá: {len(downs)}",
    ]
    if ups:
        parts.append(f"- Tăng mạnh nhất: {ups[0].material_name} ({ups[0].change_pct:+.2f}%)")
    if downs:
        parts.append(f"- Giảm mạnh nhất: {downs[0].material_name} ({downs[0].change_pct:+.2f}%)")
    parts += ["", "## Bảng giá chi tiết", "", table, "",
              "_Báo cáo cơ bản (chưa bật phân tích AI — cấu hình ANTHROPIC_API_KEY để bật)._"]
    return "\n".join(parts)
