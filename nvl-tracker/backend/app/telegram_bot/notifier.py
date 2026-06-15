"""Gửi tin nhắn & file tới Telegram (push notification)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
API = "https://api.telegram.org/bot{token}/{method}"


def _enabled() -> bool:
    return get_settings().has_telegram


def send_message(text: str, chat_id: Optional[str] = None) -> bool:
    """Gửi tin nhắn văn bản. Trả về True nếu thành công."""
    settings = get_settings()
    if not _enabled():
        logger.info("Telegram chưa cấu hình — bỏ qua gửi tin nhắn.")
        return False
    chat_id = chat_id or settings.telegram_chat_id
    # Telegram giới hạn 4096 ký tự / tin nhắn.
    for chunk in _split(text, 4000):
        try:
            r = httpx.post(
                API.format(token=settings.telegram_bot_token, method="sendMessage"),
                json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
                timeout=30,
            )
            r.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.error("Lỗi gửi Telegram: %s", exc)
            return False
    return True


def send_document(path: str, caption: str = "", chat_id: Optional[str] = None) -> bool:
    """Gửi file (vd báo cáo .docx)."""
    settings = get_settings()
    if not _enabled():
        logger.info("Telegram chưa cấu hình — bỏ qua gửi file.")
        return False
    chat_id = chat_id or settings.telegram_chat_id
    p = Path(path)
    if not p.exists():
        logger.error("Không tìm thấy file %s để gửi", path)
        return False
    try:
        with p.open("rb") as f:
            r = httpx.post(
                API.format(token=settings.telegram_bot_token, method="sendDocument"),
                data={"chat_id": chat_id, "caption": caption[:1024]},
                files={"document": (p.name, f)},
                timeout=120,
            )
        r.raise_for_status()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Lỗi gửi file Telegram: %s", exc)
        return False


def _split(text: str, size: int) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)] or [""]
