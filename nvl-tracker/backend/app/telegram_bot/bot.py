"""Bot Telegram nhận lệnh: chạy cập nhật, xem giá, lấy báo cáo.

Chạy:  python -m app.telegram_bot.bot
Yêu cầu: TELEGRAM_BOT_TOKEN. Dùng long-polling (không cần webhook).
"""

from __future__ import annotations

import logging

from app.config import get_settings
from app.db import get_repository

logger = logging.getLogger(__name__)

HELP = (
    "🤖 *Bot giá NVL*\n\n"
    "/capnhat — Chạy cập nhật giá ngay & nhận báo cáo\n"
    "/gia — Xem bảng giá mới nhất\n"
    "/baocao — Nhận file báo cáo phân tích gần nhất\n"
    "/help — Trợ giúp"
)


async def cmd_start(update, context):  # noqa: ANN001
    await update.message.reply_markdown(HELP)


async def cmd_capnhat(update, context):  # noqa: ANN001
    await update.message.reply_text("⏳ Đang cập nhật giá, vui lòng đợi...")
    from app.service import run_update

    # Bot đã tự gửi thông báo riêng, nên tắt gửi Telegram trong service để tránh trùng.
    result = await _run_blocking(run_update, send_telegram=False)
    if not result.changes:
        await update.message.reply_text("⚠️ Không lấy được dữ liệu giá. Kiểm tra cấu hình nguồn.")
        return
    from app.service import _telegram_summary
    import datetime as _dt

    await update.message.reply_markdown(
        _telegram_summary(result.changes, _dt.datetime.now().strftime("%d/%m/%Y"))
    )
    if result.docx_path:
        with open(result.docx_path, "rb") as f:
            await update.message.reply_document(f, filename="bao-cao-NVL.docx",
                                                caption="Báo cáo phân tích")
    if result.errors:
        await update.message.reply_text("Lỗi: " + "; ".join(result.errors[:5]))


async def cmd_gia(update, context):  # noqa: ANN001
    rows = get_repository().latest_prices()
    if not rows:
        await update.message.reply_text("Chưa có dữ liệu giá. Gõ /capnhat để chạy lần đầu.")
        return
    lines = ["*Bảng giá NVL mới nhất:*", ""]
    for r in rows:
        lines.append(f"• *{r.get('material_name')}*: {float(r['price']):,.0f} {r.get('unit','')}")
    await update.message.reply_markdown("\n".join(lines))


async def cmd_baocao(update, context):  # noqa: ANN001
    reports = get_repository().list_reports(limit=1)
    if not reports or not reports[0].get("docx_path"):
        await update.message.reply_text("Chưa có báo cáo nào. Gõ /capnhat để tạo.")
        return
    rep = reports[0]
    try:
        with open(rep["docx_path"], "rb") as f:
            await update.message.reply_document(f, filename="bao-cao-NVL.docx",
                                                caption=rep.get("title", "Báo cáo"))
    except FileNotFoundError:
        await update.message.reply_markdown(rep.get("summary", "Không tìm thấy file báo cáo."))


async def _run_blocking(func, **kwargs):
    """Chạy hàm đồng bộ (crawl/AI) trong thread để không chặn vòng lặp bot."""
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(**kwargs))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if not settings.telegram_bot_token:
        raise SystemExit("Thiếu TELEGRAM_BOT_TOKEN")

    from telegram.ext import ApplicationBuilder, CommandHandler

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler(["start", "help"], cmd_start))
    app.add_handler(CommandHandler("capnhat", cmd_capnhat))
    app.add_handler(CommandHandler("gia", cmd_gia))
    app.add_handler(CommandHandler("baocao", cmd_baocao))
    logger.info("Bot Telegram đang chạy (long-polling)...")
    app.run_polling()


if __name__ == "__main__":
    main()
