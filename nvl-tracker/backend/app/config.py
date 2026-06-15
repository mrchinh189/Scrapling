"""Cấu hình ứng dụng — đọc từ biến môi trường (.env)."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Toàn bộ cấu hình hệ thống. Mọi giá trị nhạy cảm nạp qua biến môi trường."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Ứng dụng ---
    app_name: str = "NVL Price Tracker"
    timezone: str = Field(default="Asia/Ho_Chi_Minh", alias="TZ")
    api_token: str = Field(default="", alias="API_TOKEN")  # bảo vệ các route ghi/chạy

    # --- Nguồn dữ liệu ---
    sources_file: str = Field(default="sources.yaml", alias="SOURCES_FILE")

    # --- Claude API (Anthropic) ---
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-opus-4-8", alias="ANTHROPIC_MODEL")
    anthropic_effort: str = Field(default="high", alias="ANTHROPIC_EFFORT")

    # --- Telegram ---
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    # --- Supabase ---
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_key: str = Field(default="", alias="SUPABASE_KEY")

    # --- Lịch tự động (cron) ---
    schedule_enabled: bool = Field(default=True, alias="SCHEDULE_ENABLED")
    schedule_cron: str = Field(default="0 7 * * 1", alias="SCHEDULE_CRON")  # 7h sáng thứ 2

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def has_supabase(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
