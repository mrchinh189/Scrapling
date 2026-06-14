"""Nạp danh sách nguồn từ file YAML."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.config import BASE_DIR
from app.models import SourceConfig


def load_sources(path: str | Path = "sources.yaml") -> list[SourceConfig]:
    """Đọc sources.yaml, trả về danh sách SourceConfig đang bật."""
    p = Path(path)
    if not p.is_absolute():
        p = BASE_DIR / p
    if not p.exists():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    raw = data.get("sources", [])
    sources = [SourceConfig(**item) for item in raw]
    return [s for s in sources if s.enabled]
