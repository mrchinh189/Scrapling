"""Lịch chạy tự động (APScheduler) — mặc định 7h sáng thứ Hai hàng tuần."""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None


def _job() -> None:
    """Hàm chạy theo lịch — gọi pipeline cập nhật đầy đủ."""
    from app.service import run_update

    logger.info("⏰ Chạy cập nhật giá theo lịch...")
    result = run_update(send_telegram=True, make_report=True)
    logger.info("Lịch hoàn tất: status=%s, records=%d", result.status, len(result.records))


def start_scheduler() -> AsyncIOScheduler | None:
    """Khởi động scheduler nếu SCHEDULE_ENABLED. Trả về scheduler (hoặc None)."""
    global _scheduler
    settings = get_settings()
    if not settings.schedule_enabled:
        logger.info("SCHEDULE_ENABLED=false — không bật lịch tự động.")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = AsyncIOScheduler(timezone=settings.timezone)
    trigger = CronTrigger.from_crontab(settings.schedule_cron, timezone=settings.timezone)
    _scheduler.add_job(_job, trigger, id="weekly_update", replace_existing=True,
                       misfire_grace_time=3600)
    _scheduler.start()
    logger.info("Đã bật lịch tự động: cron='%s' (%s)", settings.schedule_cron, settings.timezone)
    return _scheduler


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Đã dừng scheduler.")


def main() -> None:
    """Chạy scheduler độc lập (blocking)."""
    import time

    logging.basicConfig(level=logging.INFO)
    start_scheduler()
    logger.info("Scheduler đang chạy. Ctrl+C để dừng.")
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        shutdown_scheduler()


if __name__ == "__main__":
    main()
