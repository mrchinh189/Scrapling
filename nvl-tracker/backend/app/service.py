"""Orchestrator: chạy toàn bộ pipeline cập nhật giá + phân tích + thông báo."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from app.config import get_settings
from app.db import get_repository
from app.models import PriceChange, PriceRecord, Report, RunResult
from app.report import build_analysis, build_docx
from app.scraper import load_sources, scrape_all
from app.telegram_bot import notifier

logger = logging.getLogger(__name__)


def compute_changes(records: list[PriceRecord]) -> list[PriceChange]:
    """So sánh giá vừa lấy với giá lần trước (lấy từ kho trước khi lưu lượt này)."""
    repo = get_repository()
    changes: list[PriceChange] = []
    for r in records:
        prev = repo.latest_price(r.material_code)
        prev_price = float(prev["price"]) if prev else None
        change_abs = change_pct = None
        if prev_price is not None and prev_price != 0:
            change_abs = r.price - prev_price
            change_pct = change_abs / prev_price * 100
        changes.append(
            PriceChange(
                material_code=r.material_code,
                material_name=r.material_name,
                unit=r.unit,
                current_price=r.price,
                previous_price=prev_price,
                change_abs=change_abs,
                change_pct=change_pct,
                source=r.source,
                scraped_at=r.scraped_at,
            )
        )
    return changes


def _telegram_summary(changes: list[PriceChange], period: str) -> str:
    lines = [f"*Cập nhật giá NVL — {period}*", ""]
    for c in changes:
        arrow = "➡️"
        if c.change_pct is not None:
            arrow = "🔺" if c.change_pct > 0 else ("🔻" if c.change_pct < 0 else "➡️")
        pct = f" ({c.change_pct:+.2f}%)" if c.change_pct is not None else ""
        lines.append(f"{arrow} *{c.material_name}*: {c.current_price:,.0f} {c.unit}{pct}")
    return "\n".join(lines)


def run_update(*, send_telegram: bool = True, make_report: bool = True) -> RunResult:
    """Chạy 1 lượt cập nhật giá đầy đủ.

    1. Crawl nguồn  2. So sánh giá  3. Lưu kho  4. Phân tích (Claude)
    5. Xuất DOCX    6. Gửi Telegram (văn bản + file)
    """
    settings = get_settings()
    repo = get_repository()
    run_id = uuid.uuid4().hex[:12]
    started = datetime.now(timezone.utc)
    period = datetime.now().strftime("%d/%m/%Y")

    sources = load_sources(settings.sources_file)
    if not sources:
        logger.warning("Không có nguồn nào được bật trong %s", settings.sources_file)

    records, errors = scrape_all(sources)
    changes = compute_changes(records) if records else []

    # Lưu giá SAU khi đã so sánh để không lẫn với chính lượt này.
    if records:
        repo.save_prices(records)

    report_id = None
    docx_path = None
    if make_report and changes:
        report_id = f"report-{run_id}"
        analysis = build_analysis(changes, period_label=period)
        title = f"Báo cáo phân tích giá NVL — {period}"
        try:
            docx_path = build_docx(title, analysis, changes, report_id)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"DOCX: {exc}")
            logger.error("Lỗi xuất DOCX: %s", exc)
        summary = analysis.split("\n\n")[0][:500]
        repo.save_report(
            Report(
                report_id=report_id, title=title, summary=summary,
                content_md=analysis, docx_path=docx_path,
            )
        )

    if send_telegram and changes:
        notifier.send_message(_telegram_summary(changes, period))
        if docx_path:
            notifier.send_document(docx_path, caption=f"Báo cáo phân tích giá NVL {period}")

    finished = datetime.now(timezone.utc)
    status = "failed" if (errors and not records) else ("partial" if errors else "success")
    return RunResult(
        run_id=run_id, status=status, started_at=started, finished_at=finished,
        records=records, changes=changes, errors=errors,
        report_id=report_id, docx_path=docx_path,
    )
