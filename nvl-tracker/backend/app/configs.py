"""Nạp các file cấu hình YAML trong thư mục config/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from app.config import BASE_DIR

CONFIG_DIR = BASE_DIR / "config"


@lru_cache
def _load(name: str) -> dict:
    p = CONFIG_DIR / name
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def materials() -> list[dict]:
    return _load("materials.yaml").get("materials", [])


def material_map() -> dict[str, dict]:
    return {m["key"]: m for m in materials()}


def landed_config() -> dict:
    return _load("landed.yaml")


def source_links() -> dict[str, dict]:
    return _load("source_links.yaml").get("sources", {})


def thresholds() -> dict:
    return _load("thresholds.yaml")


def source_link(name: str) -> tuple[str, str | None]:
    """Trả (label, url|None) cho một tên nguồn. Không có URL → 'form nội bộ'."""
    entry = source_links().get(name)
    if not entry:
        return (name, None)
    return (entry.get("label", name), entry.get("url"))
