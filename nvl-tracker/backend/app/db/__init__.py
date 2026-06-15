"""Chọn kho dữ liệu phù hợp: Supabase nếu đã cấu hình, ngược lại SQLite."""

from __future__ import annotations

import logging
from functools import lru_cache

from app.config import get_settings
from app.db.base import Repository

logger = logging.getLogger(__name__)


@lru_cache
def get_repository() -> Repository:
    settings = get_settings()
    if settings.has_supabase:
        from app.db.supabase_repo import SupabaseRepository

        logger.info("Dùng Supabase repository")
        return SupabaseRepository(settings.supabase_url, settings.supabase_key)

    from app.db.sqlite_repo import SQLiteRepository

    logger.info("Chưa cấu hình Supabase — dùng SQLite cục bộ")
    return SQLiteRepository()


__all__ = ["get_repository", "Repository"]
