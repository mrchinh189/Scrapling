"""Giao diện kho dữ liệu (repository)."""

from __future__ import annotations

from typing import Optional, Protocol

from app.models import PriceRecord, Report


class Repository(Protocol):
    """Hợp đồng chung cho Supabase và SQLite."""

    def save_prices(self, records: list[PriceRecord]) -> None: ...

    def latest_price(self, material_code: str, before: Optional[str] = None) -> Optional[dict]: ...

    def price_history(self, material_code: str, limit: int = 30) -> list[dict]: ...

    def latest_prices(self) -> list[dict]: ...

    def save_report(self, report: Report) -> None: ...

    def list_reports(self, limit: int = 20) -> list[dict]: ...

    def get_report(self, report_id: str) -> Optional[dict]: ...
