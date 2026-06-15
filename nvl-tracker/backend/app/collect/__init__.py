"""Collectors thu thập giá thật (ưu tiên Scrapling), fail-soft theo từng nguồn."""

from app.collect.runner import backfill, collect_all

__all__ = ["collect_all", "backfill"]
